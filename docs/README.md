# Documentation Index

This directory contains all project documentation, organized by topic.

## Cloudflare Documentation

All Cloudflare-related documentation is in the [`cloudflare/`](./cloudflare/) directory:

- **[Setup Guide](./cloudflare/setup.md)** - Complete guide for setting up Cloudflare Tunnel, DNS, and email authentication
- **[Email Health Troubleshooting](./cloudflare/email-health.md)** - Guide for diagnosing and fixing email health issues
- **[Design Choices](./cloudflare/design-choices.md)** - Architecture decisions, configuration challenges, and solutions
- **[Caddy Integration](./cloudflare/caddy-integration.md)** - How Caddy and Cloudflare Tunnel work together

### Quick Links

- [Cloudflare Tunnel Setup](./cloudflare/setup.md#step-6-create-a-cloudflare-tunnel)
- [DNS Configuration](./cloudflare/setup.md#step-2-copy-dns-records-critical---prevents-emailwebsite-issues)
- [Email Authentication (SPF, DKIM, DMARC)](./cloudflare/setup.md#step-5-set-up-google-workspace-email-authentication-spf-dkim-dmarc)
- [Caddy and Cloudflare Integration](./cloudflare/caddy-integration.md) - How they work together
- [Troubleshooting Email Issues](./cloudflare/email-health.md)

## Supabase Documentation

All Supabase-related documentation is in the [`supabase/`](./supabase/) directory:

- **[Configuration Guide](./supabase/README.md)** - Complete guide for configuring and managing Supabase, including environment variables, service access, and troubleshooting
- **[Storage Configuration](./supabase/storage.md)** - Detailed guide for Supabase Storage with S3-compatible backend, MinIO setup, bucket management, and image transformation

### Quick Links

- [Initial Setup](./supabase/README.md#initial-setup)
- [Environment Variables](./supabase/README.md#environment-variables)
- [Storage Configuration](./supabase/storage.md)
- [Accessing Services](./supabase/README.md#accessing-services)
- [Troubleshooting](./supabase/README.md#troubleshooting)

## Infisical Documentation

All Infisical-related documentation is in the [`infisical/`](./infisical/) directory:

- **[Setup Guide](./infisical/setup.md)** - Guide for setting up and using Infisical for secret management
- **[Usage Guide](./infisical/usage.md)** - Why and how we use Infisical, including secret synchronization

### Quick Links

- [Setting Up Infisical](./infisical/setup.md#step-1-generate-infisical-encryption-keys)
- [Secret Synchronization](./infisical/usage.md#secret-synchronization)
- [Why We Use Infisical](./infisical/usage.md#why-infisical)

## Setup Scripts

Setup and validation scripts are located in the [`../setup/`](../setup/) directory. See the [setup scripts README](../setup/README.md) for details.

## Main Project Documentation

For general project information, installation instructions, and usage, see the [main README](../README.md) in the project root.

