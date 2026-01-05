# Raspberry Pi Deployment Checklist

## Pre-Deployment

- [ ] Raspberry Pi OS installed and updated
- [ ] Network connectivity verified
- [ ] SSH access configured (if remote deployment)
- [ ] Sufficient disk space (at least 2GB free)
- [ ] GPIO access permissions configured

## Dependencies

- [ ] Build tools installed (build-essential, cmake)
- [ ] CURL library (libcurl4-openssl-dev)
- [ ] MQTT library (libmosquitto-dev)
- [ ] GPIO library (libgpiod-dev)
- [ ] JSON library (libjsoncpp-dev)
- [ ] FlatBuffers library (libflatbuffers-dev)
- [ ] TTS tools (espeak, pico2wave)
- [ ] MQTT broker (mosquitto)

## Build

- [ ] Source code cloned/transferred
- [ ] Build script executed successfully
- [ ] All binaries compiled without errors
- [ ] Tests pass (if applicable)

## Deployment

- [ ] Deployment script executed
- [ ] Binaries installed to /opt/ai-servis/bin
- [ ] Configuration files created
- [ ] Systemd service installed
- [ ] Service enabled on boot

## Verification

- [ ] Service starts successfully: `sudo systemctl start ai-servis`
- [ ] Service status shows running: `sudo systemctl status ai-servis`
- [ ] Core Orchestrator responds on port 8080
- [ ] Hardware Server responds on port 8081
- [ ] Web UI accessible on port 8082
- [ ] MQTT broker running on port 1883
- [ ] GPIO access working (if applicable)
- [ ] Logs show no critical errors

## Testing

- [ ] Voice commands processed correctly
- [ ] Text interface functional
- [ ] Web interface accessible
- [ ] GPIO control via TCP works
- [ ] GPIO control via MQTT works
- [ ] Service restarts automatically on failure
- [ ] Service starts on boot

## Post-Deployment

- [ ] Firewall rules configured (if needed)
- [ ] Monitoring set up (optional)
- [ ] Backup configuration created
- [ ] Documentation updated with specific deployment details

## Troubleshooting

If deployment fails:

1. Check logs: `sudo journalctl -u ai-servis -n 50`
2. Verify dependencies: `dpkg -l | grep -E "libcurl|libmosquitto|libgpiod"`
3. Test GPIO access: `gpiodetect` or `sudo ./hardware-server`
4. Check ports: `sudo netstat -tulpn | grep -E "8080|8081|8082"`
5. Verify MQTT: `sudo systemctl status mosquitto`

## Rollback

If issues occur:

```bash
# Stop service
sudo systemctl stop ai-servis
sudo systemctl disable ai-servis

# Remove service
sudo systemctl daemon-reload
sudo rm /etc/systemd/system/ai-servis.service

# Remove installation (optional)
sudo rm -rf /opt/ai-servis
```
