"""Prompt rewriter service for Z-Image-Turbo optimization using Ollama."""

import logging

import openai

logger = logging.getLogger(__name__)

# System prompt for Z-Image-Turbo prompt optimization
ZIMAGE_TURBO_SYSTEM_PROMPT = """You are a prompt engineer specializing in Z-Image-Turbo, a state-of-the-art image generation model.

Your task is to enhance user prompts for optimal image generation while preserving their original intent.

## Guidelines for Positive Prompts:

1. **Preserve character trigger words**: If the user mentions a character name (like "Alix", "Elena", etc.), keep it exactly as written - these are LoRA trigger words.

2. **Add natural photography terminology**:
   - Lighting: natural light, soft lighting, golden hour, dramatic shadows, studio lighting
   - Composition: portrait, close-up, full body, candid, dynamic angle
   - Focus: shallow depth of field, bokeh, sharp focus, cinematic

3. **Include quality keywords**:
   - detailed, high resolution, sharp, professional quality
   - photorealistic, ultra-realistic, lifelike
   - masterpiece, best quality (for artistic styles)

4. **Enhance with context**:
   - Add environmental details that complement the scene
   - Include clothing/style details if relevant
   - Add mood/atmosphere descriptors

5. **Keep prompts concise but descriptive**: Aim for 30-60 words.

## Guidelines for Negative Prompts:

Generate sensible negative prompts to avoid common artifacts:
- blurry, out of focus, low quality, pixelated
- distorted, deformed, disfigured, mutated
- bad anatomy, extra limbs, missing limbs
- watermark, text, logo, signature
- oversaturated, overexposed, underexposed
- jpeg artifacts, noise, grainy

## Output Format:

Respond with ONLY a JSON object (no markdown, no explanation):
{"positive": "your enhanced positive prompt here", "negative": "your negative prompt here"}

If the user already provides a negative prompt, incorporate it with your suggestions."""


async def rewrite_prompt_for_zimage_turbo(
    prompt: str,
    negative_prompt: str | None = None,
    character_name: str | None = None,
    llm_client: openai.AsyncOpenAI | None = None,
    llm_model: str = "llama3.2",
) -> tuple[str, str]:
    """Rewrite a prompt optimized for Z-Image-Turbo using Ollama.

    Args:
        prompt: User's original prompt
        negative_prompt: Optional user-provided negative prompt
        character_name: Optional character name to preserve (LoRA trigger word)
        llm_client: OpenAI-compatible async client (typically Ollama)
        llm_model: Model name to use for rewriting

    Returns:
        Tuple of (enhanced_positive_prompt, enhanced_negative_prompt)
    """
    if llm_client is None:
        # Return original prompt if no LLM client available
        logger.warning("No LLM client available for prompt rewriting, using original prompt")
        default_negative = (
            negative_prompt
            or "blurry, low quality, distorted, deformed, bad anatomy, watermark, text"
        )
        return prompt, default_negative

    # Build user message
    user_message = f"Enhance this prompt for Z-Image-Turbo: {prompt}"
    if character_name:
        user_message += f"\n\nIMPORTANT: Preserve the character name '{character_name}' exactly as written - it's a LoRA trigger word."
    if negative_prompt:
        user_message += f"\n\nUser's negative prompt to incorporate: {negative_prompt}"

    try:
        response = await llm_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": ZIMAGE_TURBO_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty response from LLM, using original prompt")
            return prompt, negative_prompt or "blurry, low quality, distorted"

        # Parse JSON response
        import json

        # Handle potential markdown code blocks
        content = content.strip()
        if content.startswith("```"):
            # Remove markdown code block
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            result = json.loads(content)
            enhanced_positive = result.get("positive", prompt)
            enhanced_negative = result.get(
                "negative",
                negative_prompt or "blurry, low quality, distorted, deformed, bad anatomy",
            )

            logger.info(f"Prompt rewritten: '{prompt[:50]}...' -> '{enhanced_positive[:50]}...'")
            return enhanced_positive, enhanced_negative

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON: {content[:100]}")
            # Try to extract useful content anyway
            if "positive" in content.lower():
                # Fallback: use the response as the positive prompt
                return content.strip(), negative_prompt or "blurry, low quality, distorted"
            return prompt, negative_prompt or "blurry, low quality, distorted"

    except Exception:
        logger.exception("Error rewriting prompt")
        return prompt, negative_prompt or "blurry, low quality, distorted, deformed, bad anatomy"


def get_default_negative_prompt() -> str:
    """Get the default negative prompt for Z-Image-Turbo."""
    return (
        "blurry, out of focus, low quality, pixelated, distorted, deformed, disfigured, "
        "mutated, bad anatomy, extra limbs, missing limbs, watermark, text, logo, signature, "
        "oversaturated, overexposed, underexposed, jpeg artifacts, noise, grainy"
    )
