# Security

Never commit the Telegram bot token or a personal GitHub token. Store the bot token in GitHub Actions Secrets as `TELEGRAM_BOT_TOKEN`. Store the public channel username as the repository variable `TELEGRAM_CHANNEL`.

The workflow uses the short-lived repository `GITHUB_TOKEN` for GitHub Models. Paid GitHub Models usage is not required and should remain disabled for a zero-cost MVP.
