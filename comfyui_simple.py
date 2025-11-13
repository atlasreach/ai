"""
Proper ComfyUI workflow conversion
Maps widget values to correct input names
"""
import json

def convert_workflow_to_api_format(workflow_ui):
    """Convert ComfyUI UI format to proper API format with correct input mapping"""

    # Build link map: link_id -> (source_node_id, output_slot)
    link_map = {}
    for link in workflow_ui.get("links", []):
        link_id = link[0]
        source_node = str(link[1])
        output_slot = link[2]
        link_map[link_id] = (source_node, output_slot)

    # Convert nodes to API format
    api_workflow = {}
    skip_types = ["MarkdownNote", "Note", "Reroute"]

    for node in workflow_ui["nodes"]:
        if node["type"] in skip_types:
            continue

        node_id = str(node["id"])
        api_node = {
            "class_type": node["type"],
            "inputs": {}
        }

        # Process input connections
        if "inputs" in node:
            for input_item in node["inputs"]:
                input_name = input_item["name"]
                if "link" in input_item and input_item["link"] is not None:
                    link_id = input_item["link"]
                    if link_id in link_map:
                        source_node, output_slot = link_map[link_id]
                        api_node["inputs"][input_name] = [source_node, output_slot]

        # Process widget values with proper mapping
        if "widgets_values" in node and node["widgets_values"]:
            widgets = node["widgets_values"]

            # Map based on node type and known input names
            if node["type"] == "CLIPTextEncode":
                if widgets and len(widgets) > 0:
                    api_node["inputs"]["text"] = widgets[0]

            elif node["type"] == "KSampler":
                # seed, steps, cfg, sampler_name, scheduler, denoise
                if len(widgets) >= 7:
                    api_node["inputs"]["seed"] = widgets[0]
                    api_node["inputs"]["steps"] = widgets[2]
                    api_node["inputs"]["cfg"] = widgets[3]
                    api_node["inputs"]["sampler_name"] = widgets[4]
                    api_node["inputs"]["scheduler"] = widgets[5]
                    api_node["inputs"]["denoise"] = widgets[6]

            elif node["type"] == "LoadImage":
                if widgets and len(widgets) > 0:
                    api_node["inputs"]["image"] = widgets[0]

            elif node["type"] == "SaveImage":
                if widgets and len(widgets) > 0:
                    api_node["inputs"]["filename_prefix"] = widgets[0]

            elif node["type"] == "EmptySD3LatentImage":
                if len(widgets) >= 3:
                    api_node["inputs"]["width"] = widgets[0]
                    api_node["inputs"]["height"] = widgets[1]
                    api_node["inputs"]["batch_size"] = widgets[2]

            elif node["type"] == "UNETLoader":
                if len(widgets) >= 1:
                    api_node["inputs"]["unet_name"] = widgets[0]
                if len(widgets) >= 2:
                    api_node["inputs"]["weight_dtype"] = widgets[1]

            elif node["type"] == "CLIPLoader":
                if len(widgets) >= 1:
                    api_node["inputs"]["clip_name"] = widgets[0]
                if len(widgets) >= 2:
                    api_node["inputs"]["type"] = widgets[1]
                if len(widgets) >= 3:
                    api_node["inputs"]["weight_dtype"] = widgets[2]

            elif node["type"] == "VAELoader":
                if widgets and len(widgets) > 0:
                    api_node["inputs"]["vae_name"] = widgets[0]

            elif node["type"] == "LoraLoaderModelOnly":
                if len(widgets) >= 2:
                    api_node["inputs"]["lora_name"] = widgets[0]
                    api_node["inputs"]["strength_model"] = widgets[1]

            elif node["type"] == "ModelSamplingAuraFlow":
                if widgets and len(widgets) > 0:
                    api_node["inputs"]["shift"] = widgets[0]

            elif node["type"] == "LatentUpscaleBy":
                if len(widgets) >= 2:
                    api_node["inputs"]["upscale_method"] = widgets[0]
                    api_node["inputs"]["scale_by"] = widgets[1]

        api_workflow[node_id] = api_node

    return api_workflow

def test_conversion():
    """Test the conversion with your workflow"""
    with open("/workspaces/ai/workflows/qwen instagram influencer workflow (Aiorbust).json") as f:
        workflow_ui = json.load(f)

    api_workflow = convert_workflow_to_api_format(workflow_ui)

    print("✅ Conversion complete")
    print(f"Nodes converted: {len(api_workflow)}")

    # Check a few key nodes
    for node_id, node in list(api_workflow.items())[:5]:
        print(f"Node {node_id} ({node['class_type']}):")
        print(f"  Inputs: {list(node['inputs'].keys())}")

    return api_workflow

if __name__ == "__main__":
    test_conversion()
