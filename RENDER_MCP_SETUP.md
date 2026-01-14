# Render MCP Server Setup for Deployment Monitoring

## What is Render MCP?

The Render MCP (Model Context Protocol) server allows Claude Code to directly monitor and manage your Render deployments through API integration. You can check deployment status, view logs, and monitor services without leaving your IDE.

## Setup Instructions

### 1. Get Your Render API Key

1. Go to https://dashboard.render.com/account/settings
2. Scroll to "API Keys" section
3. Click **Create API Key**
4. Give it a name: "Claude Code Integration"
5. Copy the API key (starts with `rnd_...`)

### 2. Configure MCP in Claude Desktop

**For macOS/Linux:**
Edit `~/.config/claude/mcp.json`:

```json
{
  "mcpServers": {
    "render": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-render"],
      "env": {
        "RENDER_API_KEY": "rnd_your_api_key_here"
      }
    }
  }
}
```

**For Windows:**
Edit `%APPDATA%\Claude\mcp.json`:

```json
{
  "mcpServers": {
    "render": {
      "command": "npx.cmd",
      "args": ["-y", "@modelcontextprotocol/server-render"],
      "env": {
        "RENDER_API_KEY": "rnd_your_api_key_here"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

Close and reopen Claude Desktop for the MCP server to initialize.

### 4. Available MCP Commands

Once configured, Claude can use these Render MCP tools:

**Deployment Monitoring:**
```
- render_list_services - List all your Render services
- render_get_service - Get details about a specific service
- render_list_deploys - List recent deployments
- render_get_deploy - Get details about a specific deployment
- render_get_deploy_logs - View deployment logs
```

**Service Management:**
```
- render_restart_service - Restart a service
- render_suspend_service - Suspend a service
- render_resume_service - Resume a suspended service
```

**Environment Variables:**
```
- render_list_env_vars - List environment variables for a service
- render_create_env_var - Add a new environment variable
- render_update_env_var - Update an environment variable
- render_delete_env_var - Delete an environment variable
```

## Usage Examples

### Example 1: Check Deployment Status

After pushing to GitHub, ask Claude:

```
"Check the deployment status on Render for grant-finder-api"
```

Claude will use the MCP to:
1. List your services
2. Find the grant-finder-api service
3. Get the latest deployment
4. Show you the status and logs

### Example 2: View Logs

```
"Show me the logs for the last deployment on Render"
```

Claude will fetch and display the deployment logs directly.

### Example 3: Add Environment Variable

```
"Add DEEPSEEK_API_KEY=sk-xxx to the grant-finder-api service on Render"
```

Claude will use the MCP to add the env var and trigger a redeploy.

### Example 4: Monitor Multiple Services

```
"Show me the status of all my Render services"
```

Claude will list:
- grant-finder-api (web service)
- grant-finder-worker (Celery worker)
- grant-finder-scheduler (Celery Beat)
- grant-finder-db (PostgreSQL)
- grant-finder-redis (Redis)

## Benefits

✅ **Real-time monitoring** - Check deployment status without leaving Claude Code
✅ **Quick debugging** - View logs immediately when issues occur
✅ **Fast configuration** - Add/update env vars through natural language
✅ **Service management** - Restart services if needed
✅ **Multi-service oversight** - Monitor web, worker, and cron services simultaneously

## Troubleshooting

**MCP server not connecting:**
1. Verify API key is correct in mcp.json
2. Restart Claude Desktop
3. Check `~/Library/Logs/Claude/mcp-server-render.log` (macOS) for errors

**API key permissions:**
- Ensure your Render API key has full access
- Team owners have full permissions by default

**npx command not found:**
- Install Node.js: https://nodejs.org/
- Verify with: `npx --version`

## Security Notes

🔒 **Keep your Render API key secure!**
- Never commit mcp.json to git
- Store API key in secure password manager
- Rotate API keys periodically (every 90 days)

## Alternative: GitHub Auto-Deploy Only

If you prefer **not to use MCP**, you can monitor deployments via:
1. **Render Dashboard**: https://dashboard.render.com
2. **GitHub Actions**: See deployment status in repo
3. **Render Notifications**: Enable email/Slack alerts in Render settings

The GitHub auto-deploy you set up works perfectly without MCP - MCP just adds convenience for monitoring from Claude Code.
