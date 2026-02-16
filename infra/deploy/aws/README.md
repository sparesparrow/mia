# MIA AWS Deployment Guide

This directory contains the AWS deployment infrastructure for MIA multi-site web deployment.

## Overview

The deployment creates separate websites for different customer segments:
- **Business** - Corporate/professional users
- **Family** - Family safety and protection
- **Musicians** - DJs and music professionals
- **Journalists** - Gonzo journalists (existing)
- **Team** - Internal team portal
- **Main** - Landing page with segment selection

Each segment gets its own S3 bucket and CloudFront distribution for optimal performance and security.

## Quick Start

### Prerequisites

1. **AWS CLI installed and configured**
   ```bash
   aws configure
   ```

2. **Permissions required:**
   - S3: CreateBucket, PutObject, PutBucketPolicy, PutBucketEncryption, PutPublicAccessBlock
   - CloudFront: CreateDistribution, CreateOriginAccessIdentity
   - CloudFormation: CreateStack, UpdateStack, DeleteStack

### Deploy Everything

```bash
# Make script executable
chmod +x deploy.sh

# Deploy all sites
./deploy.sh
```

### Deploy Infrastructure Only (CloudFormation)

```bash
# Create CloudFormation stack
aws cloudformation create-stack \
  --stack-name mia-web-infrastructure \
  --template-body file://cloudformation.yml \
  --parameters ParameterKey=ProjectName,ParameterValue=mia-web \
  --capabilities CAPABILITY_IAM

# Wait for completion
aws cloudformation wait stack-create-complete --stack-name mia-web-infrastructure

# Get outputs
aws cloudformation describe-stacks --stack-name mia-web-infrastructure --query 'Stacks[0].Outputs'
```

### Manual Deployment Steps

If you prefer to deploy manually:

1. **Create S3 buckets:**
   ```bash
   aws s3 mb s3://mia-web-business
   aws s3 mb s3://mia-web-family
   aws s3 mb s3://mia-web-musicians
   aws s3 mb s3://mia-web-journalists
   aws s3 mb s3://mia-web-team
   aws s3 mb s3://mia-web-main
   ```

2. **Configure buckets:**
   - Enable versioning
   - Enable server-side encryption
   - Block public access

3. **Create CloudFront distributions:**
   - One per bucket
   - HTTPS redirect enabled
   - Origin Access Identity for security

4. **Upload website files:**
   ```bash
   aws s3 sync web/customers/business/ s3://mia-web-business/
   aws s3 sync web/customers/family/ s3://mia-web-family/
   aws s3 sync web/customers/musicians/ s3://mia-web-musicians/
   aws s3 sync web/customers/journalists/ s3://mia-web-journalists/
   aws s3 sync web/team/ s3://mia-web-team/
   ```

## Architecture

```
Internet
    ↓
CloudFront Distributions (HTTPS)
    ↓
S3 Buckets (Private)
    ↓
Static Website Files
```

### Security Features

- ✅ **Private S3 buckets** - No public access
- ✅ **CloudFront OAI** - Secure origin access
- ✅ **HTTPS everywhere** - Automatic redirects
- ✅ **Server-side encryption** - AES256 encryption
- ✅ **Versioning enabled** - File history protection

### Performance Features

- ✅ **Global CDN** - CloudFront edge locations
- ✅ **Compression** - Automatic gzip/brotli
- ✅ **Caching** - Optimized cache policies
- ✅ **Price classes** - Cost optimization options

## Configuration

### Environment Variables

```bash
export AWS_REGION=us-east-1
export AWS_PROFILE=default  # or your preferred profile
```

### Custom Domain Setup

1. **Request SSL certificate:**
   ```bash
   aws acm request-certificate \
     --domain-name yourdomain.com \
     --validation-method DNS
   ```

2. **Update CloudFront distribution:**
   - Add custom domain to Alternate Domain Names
   - Select SSL certificate
   - Update DNS CNAME records

### Monitoring

Set up CloudWatch alarms:

```bash
# 5xx errors alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "CloudFront-5xx-Errors" \
  --alarm-description "Alert on high 5xx error rate" \
  --metric-name "5xxErrorRate" \
  --namespace "AWS/CloudFront" \
  --statistic "Average" \
  --period 300 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold"
```

## File Structure

```
deploy/aws/
├── deploy.sh              # Main deployment script
├── cloudformation.yml     # Infrastructure as Code
├── README.md             # This file
└── (generated files)
    ├── distributions.txt  # Deployment URLs
    └── deployment-summary.md  # Deployment report
```

## Troubleshooting

### Common Issues

1. **Access Denied errors:**
   - Check IAM permissions
   - Verify bucket policies
   - Ensure Origin Access Identity is correct

2. **Distribution not deploying:**
   - Wait for CloudFront propagation (15-30 minutes)
   - Check CloudFront status in AWS console

3. **SSL certificate issues:**
   - Ensure certificate is in us-east-1 region
   - Verify domain ownership

### Logs and Debugging

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name mia-web-infrastructure

# Check CloudFront distribution status
aws cloudfront get-distribution --id DISTRIBUTION_ID

# View S3 bucket contents
aws s3 ls s3://mia-web-business --recursive
```

### Cleanup

To remove everything:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name mia-web-infrastructure

# Or delete manually
./deploy.sh clean
```

## Cost Optimization

### S3 Costs
- Storage: ~$0.023/GB/month
- Requests: ~$0.0004 per 1,000 requests
- Data transfer: ~$0.09/GB (first 10TB)

### CloudFront Costs
- Data transfer: ~$0.085/GB (US/Europe)
- Requests: ~$0.0075 per 10,000 requests
- Price Class 100: ~$0.25/month

**Estimated monthly cost:** $10-50 for moderate traffic

## Support

For issues with this deployment:
1. Check AWS service status
2. Review CloudWatch logs
3. Verify IAM permissions
4. Check deployment script output

## Advanced Configuration

### Custom Error Pages

Add to CloudFront distribution:
```yaml
CustomErrorResponses:
  - ErrorCode: 404
    ResponseCode: 404
    ResponsePagePath: /404.html
    ErrorCachingMinTTL: 300
```

### Lambda@Edge Functions

For dynamic functionality:
```yaml
LambdaFunctionAssociations:
  - EventType: viewer-request
    LambdaFunctionARN: arn:aws:lambda:us-east-1:123456789012:function:my-function:1
```

### WAF Integration

Add Web Application Firewall:
```bash
aws wafv2 create-web-acl \
  --name "MIA-WAF" \
  --scope CLOUDFRONT \
  --default-action Allow={}
```