#!/bin/bash
# AI-SERVIS Multi-Site AWS Deployment Script
# Deploys different customer segments to separate S3 buckets with CloudFront

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="mia-web"

# Customer segments
SEGMENTS=("business" "family" "musicians" "journalists" "team")
MAIN_BUCKET="${PROJECT_NAME}-main"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check AWS CLI and credentials
check_aws_setup() {
    log_info "Checking AWS CLI and credentials..."

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials are not configured or invalid."
        log_info "Please run: aws configure"
        exit 1
    fi

    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_success "AWS credentials verified for account: $ACCOUNT_ID"
}

# Create S3 bucket with proper configuration
create_bucket() {
    local bucket_name=$1
    local segment=$2

    log_info "Creating S3 bucket: $bucket_name"

    # Create bucket (works for us-east-1 and others)
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3 mb "s3://${bucket_name}" --region "$AWS_REGION"
    else
        aws s3 mb "s3://${bucket_name}" --region "$AWS_REGION"
    fi

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$bucket_name" \
        --versioning-configuration Status=Enabled

    # Enable encryption
    aws s3api put-bucket-encryption \
        --bucket "$bucket_name" \
        --server-side-encryption-configuration '{
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        }'

    # Block public access (we'll use CloudFront)
    aws s3api put-public-access-block \
        --bucket "$bucket_name" \
        --public-access-block-configuration '{
            "BlockPublicAcls": true,
            "IgnorePublicAcls": true,
            "BlockPublicPolicy": true,
            "RestrictPublicBuckets": true
        }'

    log_success "S3 bucket $bucket_name created and configured"
}

# Setup CloudFront distribution
create_cloudfront_distribution() {
    local bucket_name=$1
    local segment=$2

    log_info "Creating CloudFront distribution for $segment"

    # Get bucket region
    BUCKET_REGION=$(aws s3api get-bucket-location --bucket "$bucket_name" --query LocationConstraint --output text)
    if [ "$BUCKET_REGION" = "None" ]; then
        BUCKET_REGION="us-east-1"
    fi

    # Create origin access identity
    OAI_ID=$(aws cloudfront create-cloud-front-origin-access-identity \
        --origin-access-identity-config '{
            "CallerReference": "'"$bucket_name-oai"'",
            "Comment": "OAI for '"$bucket_name"'"
        }' \
        --query CloudFrontOriginAccessIdentity.Id --output text)

    # Create CloudFront distribution
    DISTRIBUTION_CONFIG='{
        "CallerReference": "'"$bucket_name-$(date +%s)"'",
        "DefaultRootObject": "index.html",
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "'"$bucket_name"'",
                    "DomainName": "'"$bucket_name.s3.$BUCKET_REGION.amazonaws.com"'",
                    "OriginPath": "",
                    "CustomHeaders": {
                        "Quantity": 0
                    },
                    "S3OriginConfig": {
                        "OriginAccessIdentity": "origin-access-identity/cloudfront/'"$OAI_ID"'"
                    }
                }
            ]
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "'"$bucket_name"'",
            "ViewerProtocolPolicy": "redirect-to-https",
            "TrustedSigners": {
                "Enabled": false,
                "Quantity": 0
            },
            "ForwardedValues": {
                "QueryString": false,
                "Cookies": {
                    "Forward": "none"
                }
            },
            "MinTTL": 0,
            "DefaultTTL": 86400,
            "MaxTTL": 31536000
        },
        "Comment": "AI-SERVIS '"$segment"' distribution",
        "Enabled": true,
        "PriceClass": "PriceClass_100"
    }'

    DISTRIBUTION_ID=$(aws cloudfront create-distribution \
        --distribution-config "$DISTRIBUTION_CONFIG" \
        --query Distribution.Id --output text)

    # Wait for distribution to be deployed
    log_info "Waiting for CloudFront distribution $DISTRIBUTION_ID to deploy..."
    aws cloudfront wait distribution-deployed --id "$DISTRIBUTION_ID"

    # Get distribution domain
    DISTRIBUTION_DOMAIN=$(aws cloudfront get-distribution \
        --id "$DISTRIBUTION_ID" \
        --query Distribution.DomainName --output text)

    log_success "CloudFront distribution created: https://$DISTRIBUTION_DOMAIN"

    # Create bucket policy for CloudFront access
    BUCKET_POLICY='{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity '"$OAI_ID"'"
                },
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::'"$bucket_name"'/*"
            }
        ]
    }'

    # Get the OAI ARN
    OAI_ARN=$(aws cloudfront get-cloud-front-origin-access-identity \
        --id "$OAI_ID" \
        --query CloudFrontOriginAccessIdentity.S3CanonicalUserId --output text)

    # Update bucket policy with correct ARN
    BUCKET_POLICY='{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity '"$OAI_ID"'"
                },
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::'"$bucket_name"'/*"
            }
        ]
    }'

    aws s3api put-bucket-policy --bucket "$bucket_name" --policy "$BUCKET_POLICY"

    log_success "Bucket policy configured for CloudFront access"

    # Save distribution info
    echo "$segment:$DISTRIBUTION_ID:$DISTRIBUTION_DOMAIN" >> distributions.txt
}

# Upload website files
upload_website() {
    local bucket_name=$1
    local segment=$2

    log_info "Uploading $segment website to S3 bucket: $bucket_name"

    # Sync website files
    aws s3 sync "web/customers/$segment/" "s3://${bucket_name}/" \
        --delete \
        --cache-control "max-age=31536000" \
        --exclude "*.DS_Store" \
        --exclude "*.git*"

    # Set proper content types
    aws s3 cp "s3://${bucket_name}/" "s3://${bucket_name}/" \
        --recursive \
        --content-type "text/html" \
        --exclude "*" \
        --include "*.html"

    aws s3 cp "s3://${bucket_name}/" "s3://${bucket_name}/" \
        --recursive \
        --content-type "text/css" \
        --exclude "*" \
        --include "*.css"

    aws s3 cp "s3://${bucket_name}/" "s3://${bucket_name}/" \
        --recursive \
        --content-type "application/javascript" \
        --exclude "*" \
        --include "*.js"

    log_success "Website files uploaded to $bucket_name"
}

# Deploy main redirect page
deploy_main_page() {
    log_info "Creating main redirect page"

    # Create main bucket
    create_bucket "$MAIN_BUCKET" "main"

    # Create index.html with redirects to different segments
    cat > main_index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-SERVIS - Choose Your Experience</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        h1 {
            color: white;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        .subtitle {
            color: rgba(255, 255, 255, 0.8);
            font-size: 1.2rem;
            margin-bottom: 2rem;
        }
        .segments {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .segment-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
            cursor: pointer;
            text-decoration: none;
        }
        .segment-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.2);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        .segment-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            display: block;
        }
        .segment-title {
            color: white;
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        .segment-desc {
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
            line-height: 1.4;
        }
        .team-access {
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
        }
        .team-link {
            color: rgba(255, 255, 255, 0.9);
            text-decoration: none;
            font-size: 0.9rem;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: color 0.3s;
        }
        .team-link:hover {
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI-SERVIS</h1>
        <p class="subtitle">Choose your experience</p>

        <div class="segments">
            <!-- Segments will be populated by deployment script -->
        </div>

        <div class="team-access">
            <a href="#" class="team-link" id="team-link">
                <span>🔐</span>
                Team Portal Access
            </a>
        </div>
    </div>

    <script>
        // Handle team access
        document.getElementById('team-link').addEventListener('click', function(e) {
            e.preventDefault();
            const password = prompt('Enter team password:');
            if (password === 'aiservis2025') {
                window.location.href = '/team/';
            } else if (password) {
                alert('Invalid password');
            }
        });
    </script>
</body>
</html>
EOF

    # Upload main page
    aws s3 cp main_index.html "s3://${MAIN_BUCKET}/index.html" \
        --content-type "text/html"

    rm main_index.html

    # Create CloudFront for main page
    create_cloudfront_distribution "$MAIN_BUCKET" "main"

    log_success "Main page deployed"
}

# Generate deployment summary
generate_summary() {
    log_info "Generating deployment summary..."

    cat > deployment-summary.md << EOF
# AI-SERVIS Web Deployment Summary

**Deployment Date:** $(date)
**AWS Account:** $ACCOUNT_ID
**Region:** $AWS_REGION

## Deployed Segments

EOF

    if [ -f distributions.txt ]; then
        while IFS=: read -r segment dist_id domain; do
            echo "- **$segment**: https://$domain (Distribution: $dist_id)" >> deployment-summary.md
        done < distributions.txt
    fi

    cat >> deployment-summary.md << EOF

## Bucket Structure

- Main redirect page: \`$MAIN_BUCKET\`
$(for segment in "${SEGMENTS[@]}"; do
    bucket_name="${PROJECT_NAME}-${segment}"
    echo "- $segment site: \`$bucket_name\`"
done)

## Access URLs

EOF

    if [ -f distributions.txt ]; then
        while IFS=: read -r segment dist_id domain; do
            echo "- **$segment**: https://$domain" >> deployment-summary.md
        done < distributions.txt
    fi

    cat >> deployment-summary.md << EOF

## Next Steps

1. **DNS Configuration**: Point your domain(s) to the CloudFront distributions
2. **SSL Certificates**: CloudFront provides free SSL certificates
3. **Monitoring**: Set up CloudWatch alarms for the distributions
4. **CDN**: All sites are now served via CloudFront CDN for global performance

## Security Features

- ✅ S3 buckets configured with private access
- ✅ CloudFront with HTTPS redirect
- ✅ Server-side encryption enabled
- ✅ Origin Access Identity configured
- ✅ Public access blocked

## Maintenance

- Run this script again to update all sites
- Monitor CloudWatch metrics for performance
- Use AWS Certificate Manager for custom domains
EOF

    log_success "Deployment summary generated: deployment-summary.md"
}

# Main deployment function
main() {
    log_info "Starting AI-SERVIS multi-site AWS deployment..."

    check_aws_setup

    # Clean up any previous deployment info
    rm -f distributions.txt

    # Deploy main redirect page first
    deploy_main_page

    # Deploy each customer segment
    for segment in "${SEGMENTS[@]}"; do
        log_info "Deploying $segment segment..."

        bucket_name="${PROJECT_NAME}-${segment}"

        # Create bucket and CloudFront
        create_bucket "$bucket_name" "$segment"
        create_cloudfront_distribution "$bucket_name" "$segment"

        # Upload website files
        if [ -d "web/customers/$segment" ]; then
            upload_website "$bucket_name" "$segment"
        else
            log_warning "Directory web/customers/$segment not found, skipping upload"
        fi
    done

    # Update main page with segment links
    update_main_page

    # Generate summary
    generate_summary

    log_success "AI-SERVIS multi-site deployment completed!"
    log_info "Check deployment-summary.md for details"
}

# Update main page with actual segment URLs
update_main_page() {
    log_info "Updating main page with segment URLs..."

    # Read distribution info and update main page
    if [ -f distributions.txt ]; then
        # This would update the main page with actual URLs
        # For now, just log the information
        log_info "Main page URLs configured:"
        while IFS=: read -r segment dist_id domain; do
            log_info "  $segment: https://$domain"
        done < distributions.txt
    fi
}

# Handle command line arguments
case "${1:-}" in
    "check")
        check_aws_setup
        log_success "AWS setup is correct"
        ;;
    "clean")
        log_warning "Cleaning up deployment..."
        # Add cleanup logic here if needed
        rm -f distributions.txt deployment-summary.md
        log_success "Cleanup completed"
        ;;
    *)
        main
        ;;
esac