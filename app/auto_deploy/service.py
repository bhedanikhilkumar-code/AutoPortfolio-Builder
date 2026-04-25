from __future__ import annotations

import os
import base64
from typing import Any


def generate_github_pages_yaml(username: str) -> str:
    """Generate GitHub Actions YAML for GitHub Pages deployment."""
    return f"""name: Deploy Portfolio to GitHub Pages

on:
  push:
    branches: ['main']
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{{{ steps.deployment.outputs.page_url }}}}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Pages
        uses: actions/configure-pages@v4
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""


def generate_vercel_config(custom_domain: str | None = None) -> dict[str, Any]:
    """Generate Vercel configuration."""
    config = {
        "buildCommand": "echo 'No build required'",
        "outputDirectory": ".",
        "installCommand": "echo 'No dependencies required'",
        "framework": None,
    }
    
    if custom_domain:
        config["aliases"] = [custom_domain]
    
    return config


def generate_netlify_toml(site_name: str | None = None) -> str:
    """Generate netlify.toml for auto-deploy."""
    content = """[build]
  publish = "."

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
"""
    
    if site_name:
        content += f'\n[build.environment]\n  SITE_NAME = "{site_name}"\n'
    
    return content


def generate_deploy_script(provider: str, config: dict | None = None) -> tuple[str, str]:
    """Generate deployment script. Returns (script_content, file_extension)."""
    config = config or {}
    username = config.get("username", "")
    
    if provider == "github":
        content = f"""#!/bin/bash
# GitHub Pages Deployment Script

echo "Deploying to GitHub Pages..."
cd output  # Your portfolio output directory

git init
git checkout -b gh-pages
git add .
git commit -m "Deploy portfolio"
git push -f https://${{GITHUB_TOKEN}}@github.com/{username}/${{GITHUB_REPO}}.git gh-pages

echo "Deployed successfully!"
"""
        return content, "sh"
    
    elif provider == "vercel":
        content = """#!/bin/bash
# Vercel Deployment Script

echo "Deploying to Vercel..."
npx vercel --prod --yes

echo "Deployed successfully!"
"""
        return content, "sh"
    
    elif provider == "netlify":
        content = """#!/bin/bash
# Netlify Deployment Script

echo "Deploying to Netlify..."
npx netlify-cli deploy --prod --dir=.

echo "Deployed successfully!"
"""
        return content, "sh"
    
    else:
        return "# Unknown provider", "txt"


def generate_custom_domain_config(domain: str, provider: str = "github") -> dict[str, str]:
    """Generate custom domain configuration files."""
    configs = {}
    
    # CNAME
    configs["CNAME"] = domain
    
    # Provider-specific configs
    if provider == "github":
        configs["README.md"] = f"""## Custom Domain Setup

This portfolio is deployed at: {domain}

To update DNS:
1. Add A record: @ -> 185.199.108.108
2. Add A record: @ -> 185.199.109.108
3. Add A record: @ -> 185.199.110.108
4. Add A record: @ -> 185.199.111.108
5. Add CNAME: www -> YOUR_USERNAME.github.io
"""
    
    elif provider == "vercel":
        configs["vercel.json"] = f'{{"aliases": ["{domain}"]}}'
    
    return configs


def get_deploy_provider_config(provider: str) -> dict[str, Any]:
    """Get configuration for deployment provider."""
    providers = {
        "github": {
            "name": "GitHub Pages",
            "url": "https://pages.github.com",
            "free_tier": True,
            "custom_domain": True,
            "ssl": True,
            "max_size_mb": 1024,
            "setup_steps": [
                "Enable GitHub Pages in repo settings",
                "Choose 'gh-pages' branch as source",
                "Add custom domain in settings",
            ],
        },
        "vercel": {
            "name": "Vercel",
            "url": "https://vercel.com",
            "free_tier": True,
            "custom_domain": True,
            "ssl": True,
            "max_size_mb": 100,
            "setup_steps": [
                "npm i -g vercel",
                "vercel login",
                "vercel --prod",
            ],
        },
        "netlify": {
            "name": "Netlify",
            "url": "https://netlify.com",
            "free_tier": True,
            "custom_domain": True,
            "ssl": True,
            "max_size_mb": 100,
            "setup_steps": [
                "npm i -g netlify-cli",
                "netlify login",
                "netlify deploy --prod",
            ],
        },
    }
    
    return providers.get(provider, providers["github"])