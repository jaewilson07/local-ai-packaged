#!/usr/bin/env python3
"""Sample script to test Discord bot selfie generation capability.

This script demonstrates the selfie generation workflow:
1. Send a message to a Discord channel asking for a selfie
2. The bot detects the request and triggers ComfyUI image generation
3. The bot sends the generated image back to Discord

Prerequisites:
- Discord bot running with selfie_generation capability enabled
- Character already added to the test channel
- ComfyUI service running with character LoRA
- Lambda server running

Configuration:
Set these environment variables in your .env file:
- DISCORD_BOT_TOKEN: Your Discord bot token
- ENABLED_CAPABILITIES: Must include "character,selfie_generation"
- LAMBDA_API_URL: URL to Lambda server (default: http://lambda-server:8000)

Usage:
    python sample/discord/test_selfie_generation.py

Note:
    This is an interactive test script. It won't send messages automatically.
    Follow the instructions printed by the script to test the feature manually.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def check_configuration():
    """Check if required configuration is present."""
    from dotenv import load_dotenv
    
    # Load .env from project root
    env_file = project_root / ".env"
    load_dotenv(env_file)
    
    required_vars = {
        "DISCORD_BOT_TOKEN": "Discord bot token",
        "LAMBDA_API_URL": "Lambda API URL (for ComfyUI access)",
    }
    
    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  - {var}: {description}")
    
    if missing:
        print("❌ Missing required environment variables:")
        print("\n".join(missing))
        print("\nAdd these to your .env file in the project root.")
        return False
    
    # Check ENABLED_CAPABILITIES
    enabled_caps = os.getenv("ENABLED_CAPABILITIES", "").lower().split(",")
    enabled_caps = [cap.strip() for cap in enabled_caps]
    
    required_caps = ["character", "selfie_generation"]
    missing_caps = [cap for cap in required_caps if cap not in enabled_caps]
    
    if missing_caps:
        print("⚠️ Missing required capabilities in ENABLED_CAPABILITIES:")
        print(f"  Current: {', '.join(enabled_caps)}")
        print(f"  Missing: {', '.join(missing_caps)}")
        print(f"\nSet ENABLED_CAPABILITIES={','.join(required_caps)} in your .env file")
        return False
    
    return True


def print_test_instructions():
    """Print instructions for manual testing."""
    print("=" * 70)
    print("🎨 Discord Bot Selfie Generation Test")
    print("=" * 70)
    print()
    print("This feature allows Discord users to request selfies from AI characters.")
    print()
    print("Example messages that trigger selfie generation:")
    print()
    print("  1. 'Hey Alix, can you send me a selfie?'")
    print("  2. '@Alix send me a picture'")
    print("  3. 'Alix, show me a photo of you at the beach'")
    print("  4. 'take a selfie Alix'")
    print()
    print("The bot will:")
    print("  • Detect the selfie request pattern")
    print("  • Identify the mentioned character")
    print("  • Extract context from your message (e.g., 'at the beach')")
    print("  • Generate an optimized prompt")
    print("  • Call ComfyUI via the generate-with-lora API")
    print("  • Send the generated image back to Discord")
    print()
    print("=" * 70)
    print("Setup Steps:")
    print("=" * 70)
    print()
    print("1. Ensure Discord bot is running:")
    print("   cd 03-apps/discord-bot")
    print("   python -m bot.main")
    print()
    print("2. Add a character to your Discord channel:")
    print("   Use /add_character command in Discord")
    print()
    print("3. Ensure character has a LoRA configured:")
    print("   Character info should have 'lora' field set")
    print()
    print("4. Ensure ComfyUI has the required model:")
    print("   The LoRA file should be in ComfyUI's loras/ directory")
    print()
    print("5. Test the feature:")
    print("   Send a message like: 'Hey Alix, can you send me a selfie?'")
    print()
    print("=" * 70)
    print("Configuration Check:")
    print("=" * 70)
    print()


def print_capability_settings():
    """Print current capability settings."""
    lambda_url = os.getenv("LAMBDA_API_URL", "http://lambda-server:8000")
    enabled_caps = os.getenv("ENABLED_CAPABILITIES", "").lower().split(",")
    enabled_caps = [cap.strip() for cap in enabled_caps if cap.strip()]
    
    print(f"Lambda API URL: {lambda_url}")
    print(f"Enabled Capabilities: {', '.join(enabled_caps)}")
    print()
    
    # Show selfie_generation settings (if available)
    print("Selfie Generation Settings:")
    print("  • Priority: 55 (before character_mention)")
    print("  • Requires: character_commands capability")
    print("  • Default LoRA: alix_character_lora_zit.safetensors")
    print("  • Batch Size: 1 image")
    print("  • Optimize Prompt: Yes")
    print("  • Upload to Immich: Yes")
    print()


def print_troubleshooting():
    """Print troubleshooting tips."""
    print("=" * 70)
    print("Troubleshooting:")
    print("=" * 70)
    print()
    print("If selfie generation doesn't work:")
    print()
    print("1. Check bot logs for errors:")
    print("   Look for 'Selfie generation capability ready' message")
    print()
    print("2. Verify workflow exists:")
    print("   GET /api/v1/comfyui/workflows")
    print("   Should return at least one workflow with parameter_overrides")
    print()
    print("3. Verify character LoRA:")
    print("   GET /api/v1/comfyui/loras")
    print("   Should list the character's LoRA file")
    print()
    print("4. Test generate-with-lora API directly:")
    print("   python sample/comfyui/generate_with_lora_streaming.py")
    print()
    print("5. Check ComfyUI service:")
    print("   docker logs comfyui")
    print()
    print("6. Verify Lambda API access:")
    print("   curl http://localhost:8000/api/v1/health")
    print()
    print("=" * 70)


def main():
    """Main function."""
    print_test_instructions()
    
    if not check_configuration():
        print()
        print("❌ Configuration check failed. Fix the issues above and try again.")
        sys.exit(1)
    
    print("✅ Configuration looks good!")
    print()
    
    print_capability_settings()
    print_troubleshooting()
    
    print("=" * 70)
    print("Ready to Test!")
    print("=" * 70)
    print()
    print("Go to your Discord channel and send a message like:")
    print()
    print("  'Hey Alix, can you send me a selfie?'")
    print()
    print("Watch the bot logs for progress updates.")
    print("The bot should respond with a generated image within 30-60 seconds.")
    print()


if __name__ == "__main__":
    main()
