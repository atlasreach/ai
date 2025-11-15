"""
ComfyUI API service for programmatic image generation
Uses API-format prompts exported from ComfyUI (Download Prompt)
and only tweaks a few inputs (LoRA, text, sampler, image).
"""

import os
import json
import time
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

load_dotenv()

COMFYUI_API_URL = os.getenv("COMFYUI_API_URL", "http://localhost:8188")


class ComfyUIService:
    """Service for calling ComfyUI API with API-format prompt JSON."""

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = (api_url or COMFYUI_API_URL).rstrip("/")

    # -------------------------------------------------------------------------
    # 1. Loading the API prompt (exactly what the UI uses)
    # -------------------------------------------------------------------------
    def load_api_prompt(self, workflow_path: str) -> Dict[str, Any]:
        """
        Load a ComfyUI prompt that is ALREADY in API format
        (dict keyed by node id strings).

        You get this from the ComfyUI UI using:
        - "Download Prompt" / "Copy (API format)"
        """
        if not os.path.isabs(workflow_path):
            project_root = Path(__file__).parent.parent
            workflow_path = project_root / workflow_path

        with open(workflow_path, "r") as f:
            prompt = json.load(f)

        return prompt

    # -------------------------------------------------------------------------
    # 2. Helpers for building prompts from your "character" dict
    # -------------------------------------------------------------------------
    def build_prompt_from_character(
        self,
        character: Dict[str, Any],
        prompt_additions: str = "",
    ) -> str:
        """
        Build the positive prompt from stored character info + user additions.

        Expects character to look like:
        {
            "id": "milan",
            "name": "Milan",
            "trigger_word": "milan",
            "lora_file": "milan_000002000.safetensors",
            "lora_strength": 0.8,
            "character_constraints": {
                "constants": [
                    {"type": "physical", "key": "hair", "value": "blonde"},
                    ...
                ]
            }
        }
        """
        parts: List[str] = []

        # Trigger word
        if trigger_word := character.get("trigger_word"):
            parts.append(trigger_word)

        # Physical constraints, etc.
        constraints = character.get("character_constraints", {}).get(
            "constants", []
        )
        for constraint in constraints:
            if constraint.get("type") == "physical":
                value = constraint.get("value")
                if value:
                    parts.append(value)

        # User extra text
        if prompt_additions:
            parts.append(prompt_additions)

        return ", ".join(parts)

    # -------------------------------------------------------------------------
    # 3. API-prompt injection helpers
    # -------------------------------------------------------------------------
    def api_inject_lora(
        self,
        prompt: Dict[str, Any],
        lora_file: str,
        strength: float = 0.8,
        lora_node_id: str = "74",
    ) -> None:
        """
        Set LoRA name + strength in API prompt.

        Default node id "74" is from your current workflow.
        """
        node = prompt.get(lora_node_id)
        if node and node.get("class_type") == "LoraLoaderModelOnly":
            node_inputs = node.setdefault("inputs", {})
            node_inputs["lora_name"] = lora_file
            node_inputs["strength_model"] = strength
            print(f"   ✓ Injected LoRA: {lora_file} (strength: {strength})")
        else:
            print(
                f"   ⚠ LoRA node {lora_node_id} not found or not LoraLoaderModelOnly"
            )

    def api_inject_prompts(
        self,
        prompt: Dict[str, Any],
        positive: str,
        negative: str = "",
    ) -> None:
        """
        Set positive/negative CLIP text based on node IDs.
        Node 6 = positive, Node 7 = negative in your workflow.
        """
        # Node 6 is positive prompt
        node_6 = prompt.get("6")
        if node_6 and node_6.get("class_type") == "CLIPTextEncode":
            inputs = node_6.setdefault("inputs", {})
            inputs["text"] = positive
            print(f"   ✓ Injected positive prompt: {positive[:60]}...")

        # Node 7 is negative prompt
        node_7 = prompt.get("7")
        if node_7 and node_7.get("class_type") == "CLIPTextEncode":
            inputs = node_7.setdefault("inputs", {})
            inputs["text"] = negative
            if negative:
                print(f"   ✓ Injected negative prompt: {negative[:60]}...")

    def api_inject_input_image(
        self,
        prompt: Dict[str, Any],
        image_filename: Optional[str],
        load_image_node_id: str = "76",
        ksampler_node_id: str = "3",
        text_latent_node_id: str = "58",
    ) -> None:
        """
        Inject or disable the image path.

        If `image_filename` is provided:
          - Set LoadImage node's `image` input.

        If not provided:
          - Switch the KSampler's latent to a text-only latent node
            (e.g. EmptySD3LatentImage, id "58" in your graph).
        """
        if image_filename:
            node = prompt.get(load_image_node_id)
            if node and node.get("class_type") == "LoadImage":
                node_inputs = node.setdefault("inputs", {})
                node_inputs["image"] = image_filename
                print(f"   ✓ Injected input image: {image_filename}")
            else:
                print(
                    f"   ⚠ LoadImage node {load_image_node_id} not found or wrong class_type"
                )
        else:
            # Switch to text-only latent
            ksampler = prompt.get(ksampler_node_id)
            if ksampler and ksampler.get("class_type") == "KSampler":
                k_inputs = ksampler.setdefault("inputs", {})
                # ["58", 0] means "take output 0 of node 58"
                k_inputs["latent_image"] = [text_latent_node_id, 0]
                print(
                    f"   ✓ Switched KSampler {ksampler_node_id} to text-only latent (node {text_latent_node_id})"
                )
            else:
                print(
                    f"   ⚠ KSampler node {ksampler_node_id} not found or wrong class_type"
                )

    def api_apply_sampler_overrides(
        self,
        prompt: Dict[str, Any],
        overrides: Dict[str, Any],
        ksampler_node_id: str = "3",
    ) -> None:
        """
        Override KSampler parameters for this API prompt.

        overrides can contain:
        - seed: int
        - steps: int
        - cfg: float
        - sampler_name: str
        - scheduler: str
        - denoise: float
        """
        node = prompt.get(ksampler_node_id)
        if not node or node.get("class_type") != "KSampler":
            print(
                f"   ⚠ KSampler node {ksampler_node_id} not found or wrong class_type"
            )
            return

        inputs = node.setdefault("inputs", {})
        changes = []

        if "seed" in overrides:
            inputs["seed"] = overrides["seed"]
            changes.append(f"seed={overrides['seed']}")
        if "steps" in overrides:
            inputs["steps"] = overrides["steps"]
            changes.append(f"steps={overrides['steps']}")
        if "cfg" in overrides:
            inputs["cfg"] = overrides["cfg"]
            changes.append(f"cfg={overrides['cfg']}")
        if "sampler_name" in overrides:
            inputs["sampler_name"] = overrides["sampler_name"]
            changes.append(f"sampler={overrides['sampler_name']}")
        if "scheduler" in overrides:
            inputs["scheduler"] = overrides["scheduler"]
            changes.append(f"scheduler={overrides['scheduler']}")
        if "denoise" in overrides:
            inputs["denoise"] = overrides["denoise"]
            changes.append(f"denoise={overrides['denoise']}")

        node["inputs"] = inputs

        if changes:
            print("   ✓ Sampler overrides:", ", ".join(changes))

    # -------------------------------------------------------------------------
    # 4. ComfyUI API calls
    # -------------------------------------------------------------------------
    async def submit_prompt(self, api_prompt: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit an API-format prompt to ComfyUI.

        `api_prompt` must already be a dict keyed by node id.
        """
        try:
            payload = {
                "prompt": api_prompt,
                "client_id": f"agent2_{int(time.time())}",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/prompt",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"ComfyUI API error: {response.status} - {error_text}",
                        }

                    result = await response.json()

                    if "prompt_id" in result:
                        return {"success": True, "prompt_id": result["prompt_id"]}
                    return {
                        "success": False,
                        "error": f"No prompt_id in response: {result}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution history for a prompt_id.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/history/{prompt_id}",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        history = await response.json()
                        return history.get(prompt_id)
                    return None
        except Exception as e:
            print(f"Error getting history: {e}")
            return None

    async def poll_for_completion(
        self,
        prompt_id: str,
        timeout: int = 600,
        poll_interval: int = 2,
    ) -> Dict[str, Any]:
        """
        Poll ComfyUI until generation is complete.
        """
        start_time = time.time()
        print(f"   🔄 Polling for completion (prompt_id: {prompt_id[:8]}...)")

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                return {
                    "success": False,
                    "status": "timeout",
                    "error": f"Generation timed out after {timeout}s",
                }

            history = await self.get_history(prompt_id)

            if history:
                status = history.get("status", {})
                if status.get("completed", False):
                    outputs = history.get("outputs", {})
                    output_images: List[Dict[str, Any]] = []

                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            output_images.extend(node_output["images"])

                    processing_time = time.time() - start_time
                    print(
                        f"   ✅ Generation complete in {processing_time:.1f}s"
                    )
                    print(f"   Generated {len(output_images)} image(s)")

                    return {
                        "success": True,
                        "status": "completed",
                        "output_images": output_images,
                        "processing_time": processing_time,
                    }

                if "error" in status or status.get("status_str") == "error":
                    return {
                        "success": False,
                        "status": "failed",
                        "error": status.get(
                            "error", "Unknown error during generation"
                        ),
                    }

            await asyncio.sleep(poll_interval)

    def get_image_url(self, image_info: Dict[str, Any]) -> str:
        """
        Build image URL from ComfyUI output info.

        image_info: {"filename": str, "subfolder": str, "type": str}
        """
        filename = image_info["filename"]
        subfolder = image_info.get("subfolder", "")
        type_folder = image_info.get("type", "output")

        if subfolder:
            return (
                f"{self.api_url}/view?filename={filename}"
                f"&subfolder={subfolder}&type={type_folder}"
            )
        return f"{self.api_url}/view?filename={filename}&type={type_folder}"

    # -------------------------------------------------------------------------
    # 5. Top-level convenience method
    # -------------------------------------------------------------------------
    async def generate(
        self,
        character: Dict[str, Any],
        workflow_path: str = "workflows/qwen/instagram_api_fast.json",
        input_image_filename: Optional[str] = None,
        prompt_additions: str = "",
        sampler_overrides: Optional[Dict[str, Any]] = None,
        lora_strength_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Complete generation workflow: load API prompt, inject values,
        submit, poll, and return image URLs.
        """
        try:
            print("🎨 Starting ComfyUI generation")
            print(f"   Character: {character.get('name', character.get('id'))}")
            print(f"   Workflow: {workflow_path}")

            # 1. Load API-format prompt (exactly what the UI uses)
            prompt = self.load_api_prompt(workflow_path)

            # 2. Inject LoRA
            if lora_file := character.get("lora_file"):
                lora_strength = (
                    lora_strength_override
                    if lora_strength_override is not None
                    else character.get("lora_strength", 0.8)
                )
                self.api_inject_lora(prompt, lora_file, lora_strength)

            # 3. Build positive/negative prompts and inject
            positive_prompt = self.build_prompt_from_character(
                character, prompt_additions
            )
            negative_prompt = (
                "blurry, low quality, distorted, deformed, disfigured"
            )
            self.api_inject_prompts(prompt, positive_prompt, negative_prompt)

            # 4. Inject or switch image latent
            self.api_inject_input_image(prompt, input_image_filename)

            # 5. Apply sampler overrides (steps, cfg, etc.) if provided
            if sampler_overrides:
                self.api_apply_sampler_overrides(prompt, sampler_overrides)

            # 6. Submit to ComfyUI
            print("   📤 Submitting to ComfyUI...")
            submit_result = await self.submit_prompt(prompt)
            if not submit_result["success"]:
                return submit_result

            prompt_id = submit_result["prompt_id"]
            print(f"   ✓ Submitted (prompt_id: {prompt_id[:8]}...)")

            # 7. Poll for completion
            poll_result = await self.poll_for_completion(prompt_id)
            if not poll_result["success"]:
                return poll_result

            # 8. Build output URLs
            output_images = poll_result["output_images"]
            output_urls = [self.get_image_url(img) for img in output_images]

            # If multiple images for some reason, keep the last one as "primary"
            primary_url = output_urls[-1] if output_urls else None

            return {
                "success": True,
                "output_url": primary_url,
                "output_urls": output_urls,
                "output_images": output_images,
                "processing_time": poll_result["processing_time"],
                "prompt_id": prompt_id,
            }

        except Exception as e:
            print(f"   ❌ Generation failed: {e}")
            return {"success": False, "error": str(e)}
