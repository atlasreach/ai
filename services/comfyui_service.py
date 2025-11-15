"""
ComfyUI API service for programmatic image generation
Dynamically loads workflows and injects character parameters
"""
import os
import json
import time
import asyncio
import aiohttp
import websockets
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

COMFYUI_API_URL = os.getenv('COMFYUI_API_URL', 'http://localhost:8188')

class ComfyUIService:
    """Service for calling ComfyUI API with dynamic workflow injection"""

    def __init__(self, api_url: str = None):
        self.api_url = api_url or COMFYUI_API_URL
        self.api_url = self.api_url.rstrip('/')

    def load_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """
        Load workflow JSON from file

        Args:
            workflow_path: Path to workflow JSON (relative or absolute)

        Returns:
            Workflow dictionary
        """
        # Handle relative paths from project root
        if not os.path.isabs(workflow_path):
            project_root = Path(__file__).parent.parent
            workflow_path = project_root / workflow_path

        with open(workflow_path, 'r') as f:
            workflow = json.load(f)

        return workflow

    def inject_lora(self, workflow: Dict[str, Any], lora_file: str, strength: float = 0.8) -> Dict[str, Any]:
        """
        Inject LoRA file and strength into workflow

        Args:
            workflow: Workflow dictionary
            lora_file: LoRA filename (e.g., "milan_000002000.safetensors")
            strength: LoRA strength (0.0 - 1.0)

        Returns:
            Modified workflow
        """
        # Find LoraLoaderModelOnly node
        for node in workflow.get("nodes", []):
            if node.get("type") == "LoraLoaderModelOnly":
                # Update widgets_values: [lora_name, strength]
                node["widgets_values"] = [lora_file, strength]
                print(f"   ✓ Injected LoRA: {lora_file} (strength: {strength})")
                break

        return workflow

    def inject_prompt(self, workflow: Dict[str, Any], positive_prompt: str, negative_prompt: str = "") -> Dict[str, Any]:
        """
        Inject positive and negative prompts into workflow

        Args:
            workflow: Workflow dictionary
            positive_prompt: Positive prompt text
            negative_prompt: Negative prompt text (optional)

        Returns:
            Modified workflow
        """
        # Find prompt nodes
        for node in workflow.get("nodes", []):
            if node.get("type") == "CLIPTextEncode":
                title = node.get("title", "").lower()

                if "positive" in title:
                    node["widgets_values"] = [positive_prompt]
                    print(f"   ✓ Injected positive prompt: {positive_prompt[:60]}...")

                elif "negative" in title:
                    node["widgets_values"] = [negative_prompt]
                    if negative_prompt:
                        print(f"   ✓ Injected negative prompt: {negative_prompt[:60]}...")

        return workflow

    def inject_input_image(self, workflow: Dict[str, Any], image_filename: str) -> Dict[str, Any]:
        """
        Inject input image into workflow

        Args:
            workflow: Workflow dictionary
            image_filename: Image filename in ComfyUI's input directory

        Returns:
            Modified workflow
        """
        if not image_filename:
            print(f"   ⚠ No input image provided - will use text-to-image mode")
            # Disable LoadImage node for text-to-image generation
            for node in workflow.get("nodes", []):
                if node.get("type") == "LoadImage":
                    node["disabled"] = True
                elif node.get("type") == "VAEEncode":
                    node["disabled"] = True
            return workflow

        # Find LoadImage node
        for node in workflow.get("nodes", []):
            if node.get("type") == "LoadImage":
                # Update widgets_values: [filename, "image"]
                node["widgets_values"] = [image_filename, "image"]
                print(f"   ✓ Injected input image: {image_filename}")
                break

        return workflow

    def build_prompt_from_character(
        self,
        character: Dict[str, Any],
        prompt_additions: str = ""
    ) -> str:
        """
        Build prompt from character data + user additions

        Args:
            character: Character dict with trigger_word and character_constraints
            prompt_additions: Additional prompt text from user

        Returns:
            Complete prompt string
        """
        parts = []

        # Add trigger word
        if trigger_word := character.get("trigger_word"):
            parts.append(trigger_word)

        # Add character constraints
        if constraints := character.get("character_constraints", {}).get("constants", []):
            for constraint in constraints:
                if constraint.get("type") == "physical":
                    parts.append(constraint.get("value"))

        # Add user additions
        if prompt_additions:
            parts.append(prompt_additions)

        prompt = ", ".join(parts)
        return prompt

    def find_link_source(self, workflow: Dict[str, Any], link_id: int) -> Optional[list]:
        """
        Find the source node and slot for a given link ID

        Args:
            workflow: Workflow dict
            link_id: Link ID to find

        Returns:
            [source_node_id, source_slot] or None
        """
        for link in workflow.get("links", []):
            # link format: [link_id, source_node_id, source_slot, target_node_id, target_slot, link_type]
            if link[0] == link_id:
                return [str(link[1]), link[2]]  # [source_node_id, source_slot]
        return None

    def convert_workflow_to_api_format(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert workflow from JSON format to ComfyUI API format
        Simplified version that preserves more information

        Args:
            workflow: Workflow dict with nodes as array

        Returns:
            Dict keyed by node ID (as string)
        """
        # UI-only node types to skip
        UI_ONLY_NODES = ["MarkdownNote", "Note"]

        api_prompt = {}

        for node in workflow.get("nodes", []):
            node_id = str(node.get("id"))
            node_type = node.get("type")

            # Skip UI-only nodes
            if node_type in UI_ONLY_NODES:
                continue

            # Build the node structure ComfyUI expects
            api_node = {
                "class_type": node_type,
                "inputs": {}
            }

            # Handle inputs from links (connections between nodes)
            for input_def in node.get("inputs", []):
                if isinstance(input_def, dict):
                    input_name = input_def.get("name")
                    if "link" in input_def and input_def["link"] is not None:
                        # Find the source node for this link
                        source_info = self.find_link_source(workflow, input_def["link"])
                        if source_info:
                            api_node["inputs"][input_name] = source_info

            # Handle widgets_values based on node type
            widgets_values = node.get("widgets_values", [])

            if node_type == "CLIPTextEncode" and len(widgets_values) >= 1:
                # Text goes directly into inputs
                api_node["inputs"]["text"] = widgets_values[0]

            elif node_type == "LoraLoaderModelOnly" and len(widgets_values) >= 2:
                # LoRA name and strength
                api_node["inputs"]["lora_name"] = widgets_values[0]
                api_node["inputs"]["strength_model"] = widgets_values[1]

            elif node_type == "LoadImage" and len(widgets_values) >= 1:
                # Image filename
                api_node["inputs"]["image"] = widgets_values[0]

            elif node_type == "UNETLoader" and len(widgets_values) >= 1:
                api_node["inputs"]["unet_name"] = widgets_values[0]
                if len(widgets_values) >= 2:
                    api_node["inputs"]["weight_dtype"] = widgets_values[1]

            elif node_type == "CLIPLoader" and len(widgets_values) >= 1:
                api_node["inputs"]["clip_name"] = widgets_values[0]
                if len(widgets_values) >= 2:
                    api_node["inputs"]["type"] = widgets_values[1]

            elif node_type == "VAELoader" and len(widgets_values) >= 1:
                api_node["inputs"]["vae_name"] = widgets_values[0]

            elif node_type == "KSampler" and len(widgets_values) >= 7:
                api_node["inputs"]["seed"] = widgets_values[0]
                api_node["inputs"]["control_after_generate"] = widgets_values[1]
                api_node["inputs"]["steps"] = widgets_values[2]
                api_node["inputs"]["cfg"] = widgets_values[3]
                api_node["inputs"]["sampler_name"] = widgets_values[4]
                api_node["inputs"]["scheduler"] = widgets_values[5]
                api_node["inputs"]["denoise"] = widgets_values[6]

            elif node_type == "ModelSamplingAuraFlow" and len(widgets_values) >= 1:
                api_node["inputs"]["shift"] = widgets_values[0]

            elif node_type == "EmptySD3LatentImage" and len(widgets_values) >= 3:
                api_node["inputs"]["width"] = widgets_values[0]
                api_node["inputs"]["height"] = widgets_values[1]
                api_node["inputs"]["batch_size"] = widgets_values[2]

            elif node_type == "LatentUpscaleBy" and len(widgets_values) >= 2:
                api_node["inputs"]["upscale_method"] = widgets_values[0]
                api_node["inputs"]["scale_by"] = widgets_values[1]

            elif node_type in ["SaveImage", "PreviewImage"] and len(widgets_values) >= 1:
                api_node["inputs"]["filename_prefix"] = widgets_values[0]

            # VAEEncode and VAEDecode have no widgets_values, only connections
            # which are already handled above

            api_prompt[node_id] = api_node

        return api_prompt

    def debug_workflow(self, workflow: Dict[str, Any], api_workflow: Dict[str, Any]):
        """
        Debug method to see what's being sent to ComfyUI
        """
        print("\n🔍 DEBUG - Workflow Conversion:")
        print(f"   Original nodes: {len(workflow.get('nodes', []))}")
        print(f"   API nodes: {len(api_workflow)}")

        # Save to file for inspection
        debug_path = Path(__file__).parent.parent / "debug_workflow.json"
        with open(debug_path, "w") as f:
            json.dump(api_workflow, f, indent=2)
        print(f"   💾 Saved debug_workflow.json")

        # Show key nodes
        for node_id, node_data in api_workflow.items():
            class_type = node_data.get('class_type')
            if class_type in ["LoraLoaderModelOnly", "CLIPTextEncode", "LoadImage"]:
                print(f"\n   Node {node_id} ({class_type}):")
                print(f"      Inputs: {node_data.get('inputs', {})}")

    async def submit_prompt(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit workflow to ComfyUI API

        Args:
            workflow: Complete workflow with all injections

        Returns:
            {
                "success": bool,
                "prompt_id": str,
                "error": str (optional)
            }
        """
        try:
            # Convert workflow to ComfyUI API format (dict keyed by node ID)
            api_workflow = self.convert_workflow_to_api_format(workflow)

            # Debug the conversion
            self.debug_workflow(workflow, api_workflow)

            # ComfyUI expects the workflow in a specific format
            payload = {
                "prompt": api_workflow,
                "client_id": f"agent2_{int(time.time())}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/prompt",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"ComfyUI API error: {response.status} - {error_text}"
                        }

                    result = await response.json()

                    # ComfyUI returns {"prompt_id": "...", "number": N, "node_errors": {...}}
                    if "prompt_id" in result:
                        return {
                            "success": True,
                            "prompt_id": result["prompt_id"]
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"No prompt_id in response: {result}"
                        }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """
        Get execution history for a prompt

        Args:
            prompt_id: Prompt ID from submit_prompt

        Returns:
            History dict or None if not found
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/history/{prompt_id}",
                    timeout=aiohttp.ClientTimeout(total=10)
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
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """
        Poll ComfyUI until generation is complete

        Args:
            prompt_id: Prompt ID from submit_prompt
            timeout: Max seconds to wait (default 10 minutes)
            poll_interval: Seconds between polls (default 2s)

        Returns:
            {
                "success": bool,
                "status": "completed" | "failed" | "timeout",
                "output_images": [{"filename": str, "subfolder": str, "type": str}],
                "processing_time": float,
                "error": str (optional)
            }
        """
        start_time = time.time()

        print(f"   🔄 Polling for completion (prompt_id: {prompt_id[:8]}...)")

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout:
                return {
                    "success": False,
                    "status": "timeout",
                    "error": f"Generation timed out after {timeout}s"
                }

            # Get history
            history = await self.get_history(prompt_id)

            if history:
                # Check if execution is complete
                status = history.get("status", {})

                if status.get("completed", False):
                    # Get output images
                    outputs = history.get("outputs", {})
                    output_images = []

                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            output_images.extend(node_output["images"])

                    processing_time = time.time() - start_time

                    print(f"   ✅ Generation complete in {processing_time:.1f}s")
                    print(f"   Generated {len(output_images)} image(s)")

                    return {
                        "success": True,
                        "status": "completed",
                        "output_images": output_images,
                        "processing_time": processing_time
                    }

                # Check for errors
                if "error" in status or status.get("status_str") == "error":
                    return {
                        "success": False,
                        "status": "failed",
                        "error": status.get("error", "Unknown error during generation")
                    }

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    def get_image_url(self, image_info: Dict[str, Any]) -> str:
        """
        Build image URL from ComfyUI output info

        Args:
            image_info: {"filename": str, "subfolder": str, "type": str}

        Returns:
            Full URL to image
        """
        filename = image_info["filename"]
        subfolder = image_info.get("subfolder", "")
        type_folder = image_info.get("type", "output")

        # Build URL
        if subfolder:
            url = f"{self.api_url}/view?filename={filename}&subfolder={subfolder}&type={type_folder}"
        else:
            url = f"{self.api_url}/view?filename={filename}&type={type_folder}"

        return url

    async def generate(
        self,
        character: Dict[str, Any],
        workflow_path: str = "workflows/qwen/instagram_single.json",
        input_image_filename: Optional[str] = None,
        prompt_additions: str = ""
    ) -> Dict[str, Any]:
        """
        Complete generation workflow: load, inject, submit, poll

        Args:
            character: Character dict with lora_file, trigger_word, etc.
            workflow_path: Path to workflow JSON
            input_image_filename: Input image filename (in ComfyUI's input dir)
            prompt_additions: Additional prompt text

        Returns:
            {
                "success": bool,
                "output_url": str,
                "output_images": list,
                "processing_time": float,
                "prompt_id": str,
                "error": str (optional)
            }
        """
        try:
            print(f"🎨 Starting ComfyUI generation")
            print(f"   Character: {character.get('name', character.get('id'))}")
            print(f"   Workflow: {workflow_path}")

            # 1. Load workflow
            workflow = self.load_workflow(workflow_path)

            # 2. Inject LoRA
            if lora_file := character.get("lora_file"):
                lora_strength = character.get("lora_strength", 0.8)
                workflow = self.inject_lora(workflow, lora_file, lora_strength)

            # 3. Build and inject prompt
            positive_prompt = self.build_prompt_from_character(character, prompt_additions)
            workflow = self.inject_prompt(workflow, positive_prompt)

            # 4. Inject input image (if provided)
            if input_image_filename:
                workflow = self.inject_input_image(workflow, input_image_filename)

            # 5. Submit to ComfyUI
            print(f"   📤 Submitting to ComfyUI...")
            submit_result = await self.submit_prompt(workflow)

            if not submit_result["success"]:
                return submit_result

            prompt_id = submit_result["prompt_id"]
            print(f"   ✓ Submitted (prompt_id: {prompt_id[:8]}...)")

            # 6. Poll for completion
            poll_result = await self.poll_for_completion(prompt_id)

            if not poll_result["success"]:
                return poll_result

            # 7. Build output URLs
            output_images = poll_result["output_images"]
            output_urls = [self.get_image_url(img) for img in output_images]

            return {
                "success": True,
                "output_url": output_urls[0] if output_urls else None,
                "output_urls": output_urls,
                "output_images": output_images,
                "processing_time": poll_result["processing_time"],
                "prompt_id": prompt_id
            }

        except Exception as e:
            print(f"   ❌ Generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
