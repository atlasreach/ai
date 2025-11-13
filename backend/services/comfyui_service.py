"""
ComfyUI Service
Handles communication with RunPod ComfyUI instance for image generation
"""

import os
import json
import uuid
import httpx
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path


class ComfyUIService:
    """Service for interacting with ComfyUI API on RunPod"""

    def __init__(self):
        self.runpod_url = os.getenv("RUNPOD_API_URL")
        if not self.runpod_url:
            raise ValueError("RUNPOD_API_URL not found in environment variables")

        self.runpod_url = self.runpod_url.rstrip('/')
        self.workflow_path = Path(__file__).parent.parent.parent / "workflows"

    def load_workflow(self, batch: bool = False) -> Dict[str, Any]:
        """
        Load ComfyUI workflow JSON

        Args:
            batch: If True, load batch generation workflow

        Returns:
            Workflow dictionary
        """
        filename = "qwen instagram influencer workflow batch generation (Aiorbust).json" if batch else "qwen instagram influencer workflow (Aiorbust).json"
        workflow_file = self.workflow_path / filename

        with open(workflow_file, 'r') as f:
            return json.load(f)

    def convert_workflow_to_api_format(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert workflow from JSON format to ComfyUI API format

        ComfyUI API expects nodes as a dictionary keyed by node ID, not an array
        """
        api_workflow = {}

        for node in workflow.get("nodes", []):
            node_id = str(node["id"])
            api_workflow[node_id] = {
                "inputs": {},
                "class_type": node["type"]
            }

            # Map widgets_values to inputs based on node type
            if "widgets_values" in node and node["widgets_values"]:
                api_workflow[node_id]["_meta"] = {
                    "widgets_values": node["widgets_values"]
                }

        # Map links to inputs
        for link in workflow.get("links", []):
            # link format: [link_id, source_node, source_slot, target_node, target_slot, type]
            if len(link) >= 5:
                target_node_id = str(link[3])
                if target_node_id in api_workflow:
                    source_node_id = str(link[1])
                    source_slot = link[2]
                    target_input_name = self._get_input_name(workflow, target_node_id, link[4])

                    if target_input_name:
                        api_workflow[target_node_id]["inputs"][target_input_name] = [source_node_id, source_slot]

        return api_workflow

    def _get_input_name(self, workflow: Dict[str, Any], node_id: str, input_index: int) -> Optional[str]:
        """Get input name from node definition"""
        for node in workflow.get("nodes", []):
            if str(node["id"]) == node_id and "inputs" in node:
                if input_index < len(node["inputs"]):
                    return node["inputs"][input_index].get("name")
        return None

    def update_workflow(
        self,
        workflow: Dict[str, Any],
        character_lora: str,
        lora_strength: float,
        positive_prompt: str,
        negative_prompt: str = "",
        reference_image_name: Optional[str] = None,
        cfg_scale: float = 4.0,
        steps: int = 30,
        denoise: float = 0.85,
        seed: int = -1,
        batch_size: int = 1
    ) -> Dict[str, Any]:
        """
        Update workflow with generation parameters

        Args:
            workflow: Base workflow dictionary
            character_lora: LoRA model filename
            lora_strength: LoRA strength (0.1-2.0)
            positive_prompt: Main generation prompt
            negative_prompt: Negative prompt
            reference_image_name: Reference image filename (if uploaded to ComfyUI)
            cfg_scale: CFG scale (1.0-20.0)
            steps: Sampling steps (10-100)
            denoise: Denoise strength (0.0-1.0)
            seed: Random seed (-1 for random)
            batch_size: Number of images to generate

        Returns:
            Updated workflow dictionary
        """
        # Generate random seed if needed
        if seed == -1:
            seed = int.from_bytes(os.urandom(4), 'big') % (2**32)

        for node in workflow["nodes"]:
            node_id = node.get("id")

            # Node 74: LoRA Loader
            if node_id == 74:
                node["widgets_values"][0] = character_lora
                node["widgets_values"][1] = lora_strength

            # Node 6: Positive Prompt
            elif node_id == 6:
                node["widgets_values"][0] = positive_prompt

            # Node 7: Negative Prompt
            elif node_id == 7:
                node["widgets_values"][0] = negative_prompt

            # Node 3: Main KSampler
            elif node_id == 3:
                node["widgets_values"][0] = seed  # seed
                node["widgets_values"][2] = steps  # steps
                node["widgets_values"][3] = cfg_scale  # cfg
                node["widgets_values"][6] = denoise  # denoise

            # Node 76: Reference Image Loader (if provided)
            elif node_id == 76 and reference_image_name:
                node["widgets_values"][0] = reference_image_name

            # Node 83: Batch Size (if using batch workflow)
            elif node_id == 83:
                node["widgets_values"][0] = batch_size

        return workflow

    async def queue_prompt(
        self,
        workflow: Dict[str, Any],
        client_id: Optional[str] = None
    ) -> str:
        """
        Send workflow to ComfyUI and queue for generation

        Args:
            workflow: Prepared workflow dictionary
            client_id: Optional client ID for tracking

        Returns:
            Prompt ID for tracking generation
        """
        if not client_id:
            client_id = str(uuid.uuid4())

        payload = {
            "prompt": workflow,
            "client_id": client_id
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.runpod_url}/prompt",
                    json=payload
                )

                response.raise_for_status()
                result = response.json()

                if "prompt_id" in result:
                    return result["prompt_id"]
                else:
                    raise Exception(f"No prompt_id in response: {result}")

        except Exception as e:
            print(f"Error queuing prompt: {e}")
            raise

    async def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get generation history/status

        Args:
            prompt_id: ID from queue_prompt

        Returns:
            History dictionary or None
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.runpod_url}/history/{prompt_id}"
                )

                if response.status_code == 200:
                    history = response.json()
                    return history.get(prompt_id)

                return None

        except Exception as e:
            print(f"Error getting history: {e}")
            return None

    async def wait_for_completion(
        self,
        prompt_id: str,
        timeout: int = 300,
        poll_interval: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for generation to complete

        Args:
            prompt_id: ID from queue_prompt
            timeout: Maximum wait time in seconds
            poll_interval: Seconds between status checks

        Returns:
            Completed history or None if timeout
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                print(f"Generation timeout after {timeout}s")
                return None

            # Get current status
            history = await self.get_history(prompt_id)

            if history and "outputs" in history:
                # Generation complete
                return history

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    def extract_image_urls(self, history: Dict[str, Any]) -> list:
        """
        Extract generated image URLs from history

        Args:
            history: Completed generation history

        Returns:
            List of image URLs
        """
        image_urls = []

        if "outputs" not in history:
            return image_urls

        for node_id, node_output in history["outputs"].items():
            if "images" in node_output:
                for image_info in node_output["images"]:
                    # ComfyUI image URL format
                    filename = image_info.get("filename")
                    subfolder = image_info.get("subfolder", "")
                    type_ = image_info.get("type", "output")

                    if filename:
                        url = f"{self.runpod_url}/view?filename={filename}&subfolder={subfolder}&type={type_}"
                        image_urls.append(url)

        return image_urls

    async def download_image(self, image_url: str) -> bytes:
        """
        Download generated image from ComfyUI

        Args:
            image_url: ComfyUI image URL

        Returns:
            Image bytes
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return response.content

        except Exception as e:
            print(f"Error downloading image: {e}")
            raise

    async def upload_reference_image(self, image_bytes: bytes, filename: str) -> bool:
        """
        Upload reference image to ComfyUI input folder

        Args:
            image_bytes: Image data
            filename: Target filename

        Returns:
            Success boolean
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                files = {"image": (filename, image_bytes, "image/png")}

                response = await client.post(
                    f"{self.runpod_url}/upload/image",
                    files=files
                )

                response.raise_for_status()
                return True

        except Exception as e:
            print(f"Error uploading reference image: {e}")
            return False
