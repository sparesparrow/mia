# 🚀 MIA Deployment Checklist for ai.sparetools.dev

## Pre-Deployment Setup

### 1. AWS Infrastructure
- [ ] Run `./aws-setup-commands.sh` to create S3 bucket and request certificate
- [ ] Validate DNS records in ACM console (us-east-1 region)
- [ ] Create CloudFront distribution pointing to S3 bucket
- [ ] Add DNS record: `ai.sparetools.dev` → ALIAS → `<cloudfront-domain>.cloudfront.net`

### 2. GitHub Secrets
Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):
- [ ] `AWS_ACCESS_KEY_ID` - Your AWS access key
- [ ] `AWS_SECRET_ACCESS_KEY` - Your AWS secret key  
- [ ] `CLOUDFRONT_DISTRIBUTION_ID` - Your CloudFront distribution ID

## Deployment URLs

After successful deployment, verify these endpoints:

- [ ] `https://ai.sparetools.dev/business-car/` - Business variant
- [ ] `https://ai.sparetools.dev/gonzo-car/` - Gonzo (journalists) variant  
- [ ] `https://ai.sparetools.dev/family-car/` - Family variant
- [ ] `https://ai.sparetools.dev/dj-car/` - Musicians (DJ) variant

## Variant Mapping

| Variant Name | i18n File | Theme | URL Path |
|--------------|-----------|-------|----------|
| business-car | business.yaml | corporate | /business-car/ |
| gonzo-car | gonzo.yaml | gonzo | /gonzo-car/ |
| family-car | family.yaml | family | /family-car/ |
| dj-car | musicians.yaml | creative | /dj-car/ |

## Testing Checklist

### GitHub Actions Workflow
- [ ] Workflow runs successfully on push to `main` or `feature/journalists-audio-autoplay`
- [ ] All 4 variants build without errors
- [ ] S3 sync completes successfully
- [ ] CloudFront invalidation completes
- [ ] Deployment verification step passes

### Manual Testing
- [ ] All pages load correctly with proper styling
- [ ] Czech and English translations display properly
- [ ] CSS themes apply correctly (especially Gonzo theme)
- [ ] JavaScript functionality works
- [ ] Mobile responsiveness works

### Performance Testing
- [ ] Pages load quickly (< 3 seconds)
- [ ] CloudFront caching works properly
- [ ] SSL certificate is valid and trusted

## Troubleshooting

### Common Issues
1. **Certificate not found**: Ensure certificate is in `us-east-1` region
2. **S3 access denied**: Check bucket policy and CloudFront origin access
3. **404 errors**: Verify CloudFront distribution paths and S3 folder structure
4. **CSS not loading**: Check CSS file paths in build output

### Debug Commands
```bash
# Check S3 bucket contents
aws s3 ls s3://ai-sparetools-web/ --recursive

# Check CloudFront distribution
aws cloudfront get-distribution --id <DISTRIBUTION_ID>

# Test endpoints locally
curl -I https://ai.sparetools.dev/business-car/
```

## Success Criteria

✅ **Deployment is successful when:**
- All 4 variant URLs return HTTP 200
- Pages display with correct styling and translations
- CloudFront cache invalidation works
- SSL certificate is valid
- GitHub Actions workflow completes without errors

🎉 **Ready for production!**
