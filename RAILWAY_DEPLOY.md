# Quick Deploy Guide: Railway

## ⚡ 5-Minute Deployment

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### Step 2: Deploy on Railway

1. **Go to [railway.app](https://railway.app)**
2. **Sign up** (free with GitHub)
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Select your repository**
6. **Railway auto-detects Python** ✅

### Step 3: Add Environment Variables

In Railway dashboard → Variables tab, add:

```
MEXC_API_KEY=your_mexc_api_key
MEXC_API_SECRET=your_mexc_api_secret
MEXC_BASE_URL=https://api.mexc.com
WEBHOOK_PORT=5000
WEBHOOK_HOST=0.0.0.0
POSITION_SIZE_PERCENT=20.0
STOP_LOSS_PERCENT=5.0
LOG_LEVEL=INFO
```

### Step 4: Get Your URL

Railway provides a URL like:
```
https://your-app-name.up.railway.app
```

### Step 5: Configure TradingView

In TradingView alert, set webhook URL to:
```
https://your-app-name.up.railway.app/webhook
```

### Step 6: Access Dashboard

Visit:
```
https://your-app-name.up.railway.app
```

## ✅ Done!

Your bot is now live and running 24/7!

## 📊 Monitor

- **Logs**: Railway dashboard → Deployments → View Logs
- **Metrics**: Railway dashboard → Metrics tab
- **Status**: Railway dashboard → Settings → Health checks

## 🔧 Troubleshooting

**Bot not starting?**
- Check logs in Railway dashboard
- Verify all environment variables are set
- Check Python version matches `runtime.txt`

**Webhook not receiving?**
- Verify URL is HTTPS (required by TradingView)
- Check Railway logs for incoming requests
- Test with: `curl -X POST https://your-app.up.railway.app/webhook -d '{"test": "data"}'`

**Exchange connection fails?**
- Verify API keys are correct
- Check API permissions (must have trading enabled)
- View logs for connection errors

## 💰 Cost

- **Free tier**: $5 credit/month (usually enough)
- **Hobby**: $5/month if you exceed free tier

## 🎯 Next Steps

1. Test webhook with TradingView
2. Monitor logs for first trade
3. Check dashboard for connection status
4. Verify balances are showing

