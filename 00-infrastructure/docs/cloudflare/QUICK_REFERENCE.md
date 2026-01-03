# Cloudflare Access for ComfyUI - Quick Reference

## What Was Implemented

### Code Changes
- ✅ Created `utils/comfyui_api_client.py` - Helper function for authenticated API calls
- ✅ Created API access audit documentation
- ✅ Updated access-setup.md with ComfyUI-specific information
- ✅ Created step-by-step implementation guide

### No Code Changes Needed
- ✅ All local scripts work unchanged (use `localhost:8188`)
- ✅ Service-to-service calls work unchanged (use `http://comfyui:8188`)
- ✅ No existing scripts use remote URLs (no breaking changes)

## What You Need to Do (Dashboard Steps)

### 1. Google OAuth Setup (5-10 minutes)
- [ ] Create OAuth app in Google Cloud Console
- [ ] Add redirect URI: `https://comfyui.datacrew.space/cdn-cgi/access/callback`
- [ ] Save Client ID and Client Secret

### 2. Cloudflare Access Setup (10-15 minutes)
- [ ] Enable Zero Trust (if not already)
- [ ] Add Google as identity provider
- [ ] Create Access application for `comfyui.datacrew.space`
- [ ] Configure policy with Google OAuth + authorized emails
- [ ] Link application to tunnel route

### 3. Service Token Setup (5 minutes)
- [ ] Create service token `comfyui-api`
- [ ] Add token to Access policy
- [ ] Store token in `.env` as `COMFYUI_ACCESS_TOKEN`

### 4. Testing (10 minutes)
- [ ] Test browser access (OAuth flow)
- [ ] Test API with service token
- [ ] Verify local scripts still work

## Quick Commands

### Test Local Access (Should Work)
```bash
python 02-compute/data/comfyui/sample_api_call.py
```

### Test Remote Access (After Setup)
```bash
export COMFYUI_ACCESS_TOKEN=your-token-here
python -c "from utils.comfyui_api_client import get_comfyui_client; \
           session = get_comfyui_client('https://comfyui.datacrew.space'); \
           print(session.get('https://comfyui.datacrew.space/ai-dock/api/queue-info').status_code)"
```

### Use Helper Function in Your Scripts
```python
from utils.comfyui_api_client import get_comfyui_client, submit_comfyui_workflow

# Automatically handles authentication
session = get_comfyui_client("https://comfyui.datacrew.space")
response = session.post("https://comfyui.datacrew.space/ai-dock/api/payload", json=workflow)
```

## Files Created/Modified

### New Files
- `utils/comfyui_api_client.py` - API helper function
- `00-infrastructure/docs/cloudflare/comfyui-api-audit.md` - Access pattern audit
- `00-infrastructure/docs/cloudflare/comfyui-access-implementation.md` - Step-by-step guide
- `00-infrastructure/docs/cloudflare/QUICK_REFERENCE.md` - This file

### Modified Files
- `00-infrastructure/docs/cloudflare/access-setup.md` - Added ComfyUI-specific section

## Rollback

If needed, disable Access instantly:
1. Go to Cloudflare dashboard → Networks → Tunnels
2. Edit `comfyui.datacrew.space` route
3. Set Access to "None"
4. Save

## Support

- Full guide: `comfyui-access-implementation.md`
- General Access guide: `access-setup.md`
- API audit: `comfyui-api-audit.md`


