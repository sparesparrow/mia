# MIA Universal Bootstrap Quick Reference

## Bootstrap Methods at a Glance

| Method | Script | Platforms | Dependencies | Internet | Speed | Reliability |
|--------|--------|-----------|--------------|----------|-------|-------------|
| **Direct Download** | `complete-bootstrap.py` | All | Python 3.8+ | Required | Medium | High |
| **Shell Script** | `tools/bootstrap.sh` | Unix-like | System tools | Required | Fast | Medium |
| **Docker** | `Dockerfile` | All | Docker | Optional | Fast | High |

## Quick Start Commands

### Direct Download (Recommended)
```bash
python3 complete-bootstrap.py
```

### Shell Script (Fastest)
```bash
chmod +x tools/bootstrap.sh
./tools/bootstrap.sh
```

### Docker (Most Reliable)
```bash
docker build -t mia-universal .
docker run -it mia-universal
```

## Repository Setup

### Cloudsmith (Primary)
```bash
export CLOUDSMITH_USERNAME="your_username"
export CLOUDSMITH_API_KEY="your_api_key"
./tools/repo-config.sh cloudsmith
```

### GitHub Packages (Fallback)
```bash
export GITHUB_USERNAME="your_username"
export GITHUB_TOKEN="your_token"
./tools/repo-config.sh github
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CLOUDSMITH_USERNAME` | Cloudsmith username | Optional |
| `CLOUDSMITH_API_KEY` | Cloudsmith API key | Optional |
| `GITHUB_USERNAME` | GitHub username | Optional |
| `GITHUB_TOKEN` | GitHub PAT | Optional |
| `MIA_BOOTSTRAP_CACHE` | Cache directory | Optional |

## Troubleshooting Quick Fixes

### Python Issues
```bash
# Install Python 3.8+
apt-get install python3.8  # Ubuntu/Debian
brew install python@3.8    # macOS
```

### Conan Issues
```bash
# Clean Conan cache
conan remove "*" -f
conan cache clean
```

### Network Issues
```bash
# Test connectivity
curl -I https://cloudsmith.io
curl -I https://pypi.org
```

### Permission Issues
```bash
# Fix permissions
chmod +x tools/*.sh
sudo chown -R $USER:$USER .
```

## Success Indicators

✅ **Bootstrap Complete**
- All dependencies installed
- Conan remotes configured
- Python packages available
- No error messages

✅ **Ready to Run**
```bash
conan install . --build=missing
python3 modules/core-orchestrator/main.py
```

## Common Error Solutions

| Error | Solution |
|-------|----------|
| `python3: command not found` | Install Python 3.8+ |
| `conan: command not found` | Run bootstrap script |
| `Connection timeout` | Check internet/proxy |
| `Authentication failed` | Verify credentials |
| `Permission denied` | Fix file permissions |
| `Disk space` | Free up space/clean cache |

## Performance Tips

- **Use shell script** for fastest setup
- **Pre-download packages** for offline install
- **Use Docker** for consistent environments
- **Set up repositories** before bootstrap
- **Clean cache** regularly

## Next Steps After Bootstrap

1. **Initialize project**: `./tools/init.sh`
2. **Install dependencies**: `conan install . --build=missing`
3. **Verify setup**: `python3 -c "import mcp_framework"`
4. **Start services**: `python3 modules/core-orchestrator/main.py`

## Getting Help

- **Logs**: Check `logs/` directory
- **Verbose output**: Run with `--help` flag
- **GitHub Issues**: Search existing issues
- **Documentation**: See `docs/BOOTSTRAP_COMPARISON.md`