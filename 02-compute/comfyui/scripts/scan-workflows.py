#!/usr/bin/env python3
"""
ComfyUI Workflow Model & Custom Node Scanner

Scans ComfyUI workflows from multiple sources (local files and Supabase database),
extracts model filenames from loader nodes, detects required custom nodes,
resolves download URLs using a multi-tier lookup strategy, and updates models.yml
with missing models.

Usage:
    # Scan all sources and update models.yml
    python scan-workflows.py

    # Scan only local workflow files
    python scan-workflows.py --source local

    # Scan only database workflows
    python scan-workflows.py --source database

    # Dry run (show what would be added)
    python scan-workflows.py --dry-run

    # Enable all URL resolution tiers
    python scan-workflows.py --civitai --searxng

    # Skip custom node detection
    python scan-workflows.py --skip-nodes

Environment Variables:
    LAMBDA_API_URL: Lambda server URL (default: http://lambda-server:8000)
    CF_ACCESS_JWT: Cloudflare Access JWT token (for external API access)
    CIVITAI_API_KEY: CivitAI API token (for CivitAI model lookup)
    HF_TOKEN: HuggingFace token (for private models)
    SEARXNG_URL: SearXNG URL (default: http://searxng:8080)
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
import yaml

# Add project root to path for sample imports
SCRIPT_DIR = Path(__file__).resolve().parent
COMFYUI_DIR = SCRIPT_DIR.parent
COMPUTE_DIR = COMFYUI_DIR.parent
PROJECT_ROOT = COMPUTE_DIR.parent

# Try to import auth helpers from sample/shared
sys.path.insert(0, str(PROJECT_ROOT))
try:
    from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
except ImportError:
    # Fallback if auth_helpers not available
    def get_api_base_url() -> str:
        return os.getenv("LAMBDA_API_URL", "http://lambda-server:8000")

    def get_auth_headers() -> dict[str, str]:
        jwt_token = os.getenv("CF_ACCESS_JWT")
        if jwt_token:
            return {"Cf-Access-Jwt-Assertion": jwt_token}
        return {}


# Default paths
DEFAULT_WORKFLOWS_DIR = COMFYUI_DIR / "config" / "workflows"
MODELS_YML_PATH = SCRIPT_DIR / "models.yml"
KNOWN_MODELS_PATH = SCRIPT_DIR / "known_models.yml"
KNOWN_NODES_PATH = SCRIPT_DIR / "known_nodes.yml"

# Built-in ComfyUI node types (not from custom nodes)
# This is a non-exhaustive list of core nodes that don't require custom node installation
BUILTIN_NODE_TYPES: set[str] = {
    # Loaders
    "CheckpointLoaderSimple",
    "CheckpointLoader",
    "VAELoader",
    "UNETLoader",
    "LoraLoader",
    "LoraLoaderModelOnly",
    "CLIPLoader",
    "DualCLIPLoader",
    "TripleCLIPLoader",
    "ControlNetLoader",
    "UpscaleModelLoader",
    "DiffusersLoader",
    "unCLIPCheckpointLoader",
    "StyleModelLoader",
    "GLIGENLoader",
    "HypernetworkLoader",
    # Samplers
    "KSampler",
    "KSamplerAdvanced",
    "SamplerCustom",
    "SamplerCustomAdvanced",
    # Latent
    "EmptyLatentImage",
    "LatentUpscale",
    "LatentUpscaleBy",
    "LatentComposite",
    "LatentBlend",
    "LatentCrop",
    "LatentFlip",
    "LatentRotate",
    "LatentBatch",
    "LatentFromBatch",
    "RepeatLatentBatch",
    "LatentBatchSeedBehavior",
    # Image
    "LoadImage",
    "SaveImage",
    "PreviewImage",
    "ImageScale",
    "ImageScaleBy",
    "ImageUpscaleWithModel",
    "ImageInvert",
    "ImageBatch",
    "ImageFromBatch",
    "RepeatImageBatch",
    "ImageCompositeMasked",
    "ImageCrop",
    "ImagePadForOutpaint",
    "EmptyImage",
    "ImageBlend",
    "ImageBlur",
    "ImageQuantize",
    "ImageSharpen",
    # CLIP
    "CLIPTextEncode",
    "CLIPTextEncodeSDXL",
    "CLIPTextEncodeFlux",
    "CLIPSetLastLayer",
    "CLIPVisionLoader",
    "CLIPVisionEncode",
    # Conditioning
    "ConditioningCombine",
    "ConditioningAverage",
    "ConditioningConcat",
    "ConditioningSetArea",
    "ConditioningSetAreaPercentage",
    "ConditioningSetAreaStrength",
    "ConditioningSetMask",
    "ConditioningZeroOut",
    "ConditioningSetTimestepRange",
    # Mask
    "MaskToImage",
    "ImageToMask",
    "ImageColorToMask",
    "SolidMask",
    "InvertMask",
    "CropMask",
    "MaskComposite",
    "FeatherMask",
    "GrowMask",
    "ThresholdMask",
    "MaskPreview",
    # VAE
    "VAEEncode",
    "VAEDecode",
    "VAEEncodeTiled",
    "VAEDecodeTiled",
    "VAEEncodeForInpaint",
    # ControlNet
    "ControlNetApply",
    "ControlNetApplyAdvanced",
    # Model
    "ModelMergeSimple",
    "ModelMergeBlocks",
    "ModelMergeSubtract",
    "ModelMergeAdd",
    "CheckpointSave",
    "CLIPMergeSimple",
    "CLIPMergeSubtract",
    "CLIPMergeAdd",
    # Utilities
    "Note",
    "Reroute",
    "PrimitiveNode",
    # Advanced
    "FreeU",
    "FreeU_V2",
    "HyperTile",
    "PatchModelAddDownscale",
    "RescaleCFG",
    "SamplerDPMPP_2M_SDE",
    "SamplerDPMPP_SDE",
    "SamplerEulerAncestral",
    "SplitSigmas",
    "SplitSigmasDenoise",
    "FlipSigmas",
    "SetLatentNoiseMask",
    "InpaintModelConditioning",
    # SDXL specific
    "SDXLRefinerEncode",
    "SDXLStyleModelApply",
    # Flux specific
    "ModelSamplingFlux",
    "FluxGuidance",
    # Video
    "SaveAnimatedWEBP",
    "SaveAnimatedPNG",
}

# Node types that load models
# Format: node_type -> list of (widget_index_or_input_key, category)
# For old format (widgets_values): widget_index is an integer
# For new API format (inputs): widget_index is the input key name

# Old format: Maps node_type -> list of (widget_index, category)
MODEL_LOADER_NODES_WIDGETS: dict[str, list[tuple[int, str]]] = {
    "CheckpointLoaderSimple": [(0, "checkpoints")],
    "CheckpointLoader": [(0, "checkpoints")],
    "VAELoader": [(0, "vae")],
    "UNETLoader": [(0, "unet")],
    "LoraLoader": [(0, "loras")],
    "LoraLoaderModelOnly": [(0, "loras")],
    "CLIPLoader": [(0, "clip")],
    "DualCLIPLoader": [(0, "clip"), (1, "clip")],
    "ControlNetLoader": [(0, "controlnet")],
    "UpscaleModelLoader": [(0, "upscale_models")],
    # Additional common loaders
    "DiffusersLoader": [(0, "checkpoints")],
    "unCLIPCheckpointLoader": [(0, "checkpoints")],
    "StyleModelLoader": [(0, "style_models")],
    "GLIGENLoader": [(0, "gligen")],
    "HypernetworkLoader": [(0, "hypernetworks")],
    "PhotoMakerLoader": [(0, "photomaker")],
    "InstantIDModelLoader": [(0, "instantid")],
    "IPAdapterModelLoader": [(0, "ipadapter")],
    "LoadIPAdapter": [(0, "ipadapter")],
    "LoadInsightFace": [(0, "insightface")],
    # GGUF loaders (ComfyUI-GGUF custom nodes)
    "UnetLoaderGGUF": [(0, "unet")],
    "CLIPLoaderGGUF": [(0, "clip")],
    "DualCLIPLoaderGGUF": [(0, "clip"), (1, "clip")],
}

# New API format: Maps node_type (class_type) -> list of (input_key, category)
MODEL_LOADER_NODES_INPUTS: dict[str, list[tuple[str, str]]] = {
    "CheckpointLoaderSimple": [("ckpt_name", "checkpoints")],
    "CheckpointLoader": [("ckpt_name", "checkpoints")],
    "VAELoader": [("vae_name", "vae")],
    "UNETLoader": [("unet_name", "unet")],
    "LoraLoader": [("lora_name", "loras")],
    "LoraLoaderModelOnly": [("lora_name", "loras")],
    "CLIPLoader": [("clip_name", "clip")],
    "DualCLIPLoader": [("clip_name1", "clip"), ("clip_name2", "clip")],
    "TripleCLIPLoader": [("clip_name1", "clip"), ("clip_name2", "clip"), ("clip_name3", "clip")],
    "ControlNetLoader": [("control_net_name", "controlnet")],
    "UpscaleModelLoader": [("model_name", "upscale_models")],
    # Additional common loaders
    "DiffusersLoader": [("model_path", "checkpoints")],
    "unCLIPCheckpointLoader": [("ckpt_name", "checkpoints")],
    "StyleModelLoader": [("style_model_name", "style_models")],
    "GLIGENLoader": [("gligen_name", "gligen")],
    "HypernetworkLoader": [("hypernetwork_name", "hypernetworks")],
    "PhotoMakerLoader": [("photomaker_model_name", "photomaker")],
    "InstantIDModelLoader": [("instantid_file", "instantid")],
    "IPAdapterModelLoader": [("ipadapter_file", "ipadapter")],
    "LoadIPAdapter": [("ipadapter_file", "ipadapter")],
    "LoadInsightFace": [("model_path", "insightface")],
    # Z-Image-Turbo and other custom nodes
    "ModelPatchLoader": [("name", "model_patches")],
    # GGUF loaders (ComfyUI-GGUF custom nodes)
    "UnetLoaderGGUF": [("unet_name", "unet")],
    "CLIPLoaderGGUF": [("clip_name", "clip")],
    "DualCLIPLoaderGGUF": [("clip_name1", "clip"), ("clip_name2", "clip")],
}


@dataclass
class ModelReference:
    """Represents a model reference found in a workflow."""

    filename: str
    category: str
    node_type: str
    workflow_source: str
    url: str | None = None
    description: str | None = None

    def __hash__(self) -> int:
        return hash((self.filename, self.category))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModelReference):
            return False
        return self.filename == other.filename and self.category == other.category


@dataclass
class CustomNodeReference:
    """Represents a custom node package required by a workflow."""

    package_name: str
    url: str
    description: str
    node_types: list[str] = field(default_factory=list)
    pip_packages: list[str] = field(default_factory=list)
    workflow_sources: list[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.package_name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CustomNodeReference):
            return False
        return self.package_name == other.package_name


@dataclass
class ScanResult:
    """Result of scanning workflows."""

    models_found: dict[str, list[ModelReference]] = field(default_factory=dict)
    resolved_models: dict[str, list[ModelReference]] = field(default_factory=dict)
    unresolved_models: dict[str, list[ModelReference]] = field(default_factory=dict)
    # Custom node tracking
    nodes_found: set[str] = field(default_factory=set)  # All node types found
    custom_nodes_required: dict[str, CustomNodeReference] = field(default_factory=dict)
    unknown_nodes: set[str] = field(default_factory=set)  # Nodes not in known_nodes.yml
    workflows_scanned: int = 0
    errors: list[str] = field(default_factory=list)


class KnownModelsDB:
    """Database of known model filenames and their URLs."""

    def __init__(self, known_models_path: Path = KNOWN_MODELS_PATH):
        self.known_models_path = known_models_path
        self.models: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load known models from YAML file."""
        if not self.known_models_path.exists():
            return

        with open(self.known_models_path) as f:
            data = yaml.safe_load(f) or {}

        for category, models in data.items():
            if not isinstance(models, list):
                continue
            for model in models:
                if isinstance(model, dict) and "name" in model:
                    key = f"{category}:{model['name']}"
                    self.models[key] = {
                        "url": model.get("url"),
                        "description": model.get("description"),
                        "category": category,
                    }
                    # Also add aliases if present
                    for alias in model.get("aliases", []):
                        alias_key = f"{category}:{alias}"
                        self.models[alias_key] = self.models[key]

    def lookup(self, filename: str, category: str) -> dict[str, Any] | None:
        """Look up a model by filename and category."""
        key = f"{category}:{filename}"
        if key in self.models:
            return self.models[key]

        # Try without category (some models might be listed under different categories)
        for stored_key, model_info in self.models.items():
            stored_cat, stored_name = stored_key.split(":", 1)
            if stored_name == filename:
                return model_info

        return None


class KnownNodesDB:
    """Database of known custom node packages and their node types."""

    def __init__(self, known_nodes_path: Path = KNOWN_NODES_PATH):
        self.known_nodes_path = known_nodes_path
        # Maps node_type -> package info
        self.node_to_package: dict[str, dict[str, Any]] = {}
        # Maps package_name -> full package info
        self.packages: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load known nodes from YAML file."""
        if not self.known_nodes_path.exists():
            return

        with open(self.known_nodes_path) as f:
            data = yaml.safe_load(f) or {}

        for package_name, package_info in data.items():
            if not isinstance(package_info, dict):
                continue

            self.packages[package_name] = {
                "url": package_info.get("url", ""),
                "description": package_info.get("description", ""),
                "pip_packages": package_info.get("pip_packages", []),
                "requirements": package_info.get("requirements"),
                "nodes": package_info.get("nodes", []),
            }

            # Map each node type to its package
            for node_type in package_info.get("nodes", []):
                self.node_to_package[node_type] = {
                    "package_name": package_name,
                    **self.packages[package_name],
                }

    def lookup_node(self, node_type: str) -> dict[str, Any] | None:
        """Look up package info for a node type."""
        return self.node_to_package.get(node_type)

    def lookup_package(self, package_name: str) -> dict[str, Any] | None:
        """Look up package info by package name."""
        return self.packages.get(package_name)

    def get_all_known_node_types(self) -> set[str]:
        """Get all known node types from all packages."""
        return set(self.node_to_package.keys())


class HuggingFaceResolver:
    """Resolve model URLs from HuggingFace."""

    # Popular model repositories to search
    POPULAR_REPOS = [
        "stabilityai",
        "black-forest-labs",
        "runwayml",
        "comfyanonymous",
        "Comfy-Org",
        "lllyasviel",
        "madebyollin",
    ]

    def __init__(self, hf_token: str | None = None):
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.session = requests.Session()
        if self.hf_token:
            self.session.headers["Authorization"] = f"Bearer {self.hf_token}"

    def search(self, filename: str, category: str) -> dict[str, str] | None:
        """Search HuggingFace for a model by filename."""
        # Try huggingface_hub if available
        try:
            from huggingface_hub import HfApi, hf_hub_url

            api = HfApi()

            # Extract base name for search (remove extension and version info)
            base_name = Path(filename).stem
            base_name = re.sub(r"[-_]v?\d+(\.\d+)*$", "", base_name)  # Remove version
            base_name = re.sub(r"[-_](fp16|fp32|bf16|Q\d+_\w+)$", "", base_name, flags=re.I)

            # Search popular repos first
            for author in self.POPULAR_REPOS:
                try:
                    models = api.list_models(author=author, search=base_name, limit=10)
                    for model in models:
                        # Check if model repo contains our file
                        try:
                            files = api.list_repo_files(model.id)
                            for f in files:
                                if f.endswith(filename) or Path(f).name == filename:
                                    url = hf_hub_url(model.id, filename=f)
                                    return {
                                        "url": url,
                                        "description": f"From HuggingFace: {model.id}",
                                    }
                        except Exception:
                            continue
                except Exception:
                    continue

            # Broader search if not found in popular repos
            try:
                models = api.list_models(search=base_name, limit=20)
                for model in models:
                    try:
                        files = api.list_repo_files(model.id)
                        for f in files:
                            if f.endswith(filename) or Path(f).name == filename:
                                url = hf_hub_url(model.id, filename=f)
                                return {
                                    "url": url,
                                    "description": f"From HuggingFace: {model.id}",
                                }
                    except Exception:
                        continue
            except Exception:
                pass

        except ImportError:
            # Fall back to REST API search
            return self._search_via_api(filename, base_name if "base_name" in dir() else filename)

        return None

    def _search_via_api(self, filename: str, search_term: str) -> dict[str, str] | None:
        """Search HuggingFace via REST API (fallback)."""
        try:
            response = self.session.get(
                "https://huggingface.co/api/models",
                params={"search": search_term, "limit": 20},
                timeout=30,
            )
            if response.status_code == 200:
                models = response.json()
                for model in models:
                    model_id = model.get("id", "")
                    # Try to get file list
                    files_response = self.session.get(
                        f"https://huggingface.co/api/models/{model_id}",
                        timeout=30,
                    )
                    if files_response.status_code == 200:
                        model_info = files_response.json()
                        siblings = model_info.get("siblings", [])
                        for sibling in siblings:
                            rfilename = sibling.get("rfilename", "")
                            if rfilename.endswith(filename) or Path(rfilename).name == filename:
                                url = f"https://huggingface.co/{model_id}/resolve/main/{rfilename}"
                                return {
                                    "url": url,
                                    "description": f"From HuggingFace: {model_id}",
                                }
        except Exception:
            pass
        return None


class CivitAIResolver:
    """Resolve model URLs from CivitAI."""

    BASE_URL = "https://civitai.com/api/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CIVITAI_API_KEY")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def search(self, filename: str, category: str) -> dict[str, str] | None:
        """Search CivitAI for a model by filename."""
        # Extract search term from filename
        base_name = Path(filename).stem
        # Clean up common suffixes
        search_term = re.sub(
            r"[-_](fp16|fp32|bf16|safetensors|ckpt|pth)$", "", base_name, flags=re.I
        )
        search_term = re.sub(r"[-_]v?\d+(\.\d+)*$", "", search_term)

        try:
            response = self.session.get(
                f"{self.BASE_URL}/models",
                params={"query": search_term, "limit": 10},
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                for item in items:
                    model_versions = item.get("modelVersions", [])
                    for version in model_versions:
                        files = version.get("files", [])
                        for f in files:
                            if (
                                f.get("name") == filename
                                or Path(f.get("name", "")).stem == base_name
                            ):
                                download_url = f.get("downloadUrl")
                                if download_url:
                                    return {
                                        "url": download_url,
                                        "description": f"From CivitAI: {item.get('name', 'Unknown')}",
                                    }
        except Exception:
            pass
        return None


class SearXNGResolver:
    """Resolve model URLs using SearXNG web search."""

    def __init__(self, searxng_url: str | None = None, lambda_api_url: str | None = None):
        self.searxng_url = searxng_url or os.getenv("SEARXNG_URL", "http://searxng:8080")
        self.lambda_api_url = lambda_api_url or get_api_base_url()
        self.session = requests.Session()

    def search(self, filename: str, category: str) -> dict[str, str] | None:
        """Search for model download URL using SearXNG."""
        # Try Lambda API first (uses internal SearXNG)
        result = self._search_via_lambda(filename)
        if result:
            return result

        # Fall back to direct SearXNG
        return self._search_direct(filename)

    def _search_via_lambda(self, filename: str) -> dict[str, str] | None:
        """Search via Lambda API SearXNG endpoint."""
        try:
            headers = get_auth_headers()
            query = f'"{filename}" huggingface OR civitai download'
            response = self.session.post(
                f"{self.lambda_api_url}/api/v1/searxng/search",
                json={"query": query, "categories": ["general"], "engines": ["google", "bing"]},
                headers=headers,
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                return self._parse_search_results(data.get("results", []), filename)
        except Exception:
            pass
        return None

    def _search_direct(self, filename: str) -> dict[str, str] | None:
        """Search directly via SearXNG."""
        try:
            query = f'"{filename}" huggingface OR civitai download'
            response = self.session.get(
                f"{self.searxng_url}/search",
                params={"q": query, "format": "json"},
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                return self._parse_search_results(data.get("results", []), filename)
        except Exception:
            pass
        return None

    def _parse_search_results(self, results: list[dict], filename: str) -> dict[str, str] | None:
        """Parse search results to find download URLs."""
        hf_pattern = re.compile(
            r"https://huggingface\.co/([^/]+/[^/]+)/(?:resolve|blob)/[^/]+/(.+)"
        )
        civitai_pattern = re.compile(r"https://civitai\.com/api/download/models/(\d+)")

        for result in results:
            url = result.get("url", "")
            title = result.get("title", "")

            # Check for HuggingFace URLs
            hf_match = hf_pattern.search(url)
            if hf_match:
                repo_id = hf_match.group(1)
                file_path = hf_match.group(2)
                if filename in file_path:
                    download_url = f"https://huggingface.co/{repo_id}/resolve/main/{file_path}"
                    return {
                        "url": download_url,
                        "description": f"From search: {title[:50]}...",
                    }

            # Check for CivitAI URLs
            civitai_match = civitai_pattern.search(url)
            if civitai_match and filename.lower() in title.lower():
                return {
                    "url": url,
                    "description": f"From CivitAI search: {title[:50]}...",
                }

        return None


class WorkflowScanner:
    """Main workflow scanner that extracts model references and custom nodes from workflows."""

    def __init__(
        self,
        workflows_dir: Path = DEFAULT_WORKFLOWS_DIR,
        known_models_db: KnownModelsDB | None = None,
        known_nodes_db: KnownNodesDB | None = None,
        use_huggingface: bool = True,
        use_civitai: bool = False,
        use_searxng: bool = False,
        scan_nodes: bool = True,
        verbose: bool = False,
    ):
        self.workflows_dir = workflows_dir
        self.known_models_db = known_models_db or KnownModelsDB()
        self.known_nodes_db = known_nodes_db or KnownNodesDB()
        self.scan_nodes = scan_nodes
        self.verbose = verbose

        # Initialize resolvers
        self.resolvers: list[tuple[str, Any]] = [("known_db", self.known_models_db)]

        if use_huggingface:
            self.resolvers.append(("huggingface", HuggingFaceResolver()))

        if use_civitai:
            self.resolvers.append(("civitai", CivitAIResolver()))

        if use_searxng:
            self.resolvers.append(("searxng", SearXNGResolver()))

    def scan_local_workflows(self) -> list[tuple[str, dict]]:
        """Scan local workflow JSON files."""
        workflows = []

        if not self.workflows_dir.exists():
            return workflows

        for workflow_path in self.workflows_dir.rglob("*.json"):
            try:
                with open(workflow_path) as f:
                    workflow_data = json.load(f)
                workflows.append((str(workflow_path), workflow_data))
                if self.verbose:
                    print(f"  Loaded: {workflow_path.name}")
            except (json.JSONDecodeError, OSError) as e:
                if self.verbose:
                    print(f"  Error loading {workflow_path}: {e}")

        return workflows

    def scan_database_workflows(self) -> list[tuple[str, dict]]:
        """Scan workflows from Supabase database via Lambda API."""
        workflows = []

        try:
            api_url = get_api_base_url()
            headers = get_auth_headers()

            response = requests.get(
                f"{api_url}/api/v1/comfyui/workflows",
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                items = data if isinstance(data, list) else data.get("items", [])

                for item in items:
                    workflow_json = item.get("workflow_json")
                    workflow_id = item.get("id", "unknown")
                    workflow_name = item.get("name", f"db-workflow-{workflow_id}")

                    if workflow_json:
                        # Handle both string and dict workflow_json
                        if isinstance(workflow_json, str):
                            try:
                                workflow_data = json.loads(workflow_json)
                            except json.JSONDecodeError:
                                continue
                        else:
                            workflow_data = workflow_json

                        workflows.append((f"database:{workflow_name}", workflow_data))
                        if self.verbose:
                            print(f"  Loaded from DB: {workflow_name}")
            elif self.verbose:
                print(f"  Failed to fetch database workflows: {response.status_code}")

        except requests.exceptions.RequestException as e:
            if self.verbose:
                print(f"  Error fetching database workflows: {e}")

        return workflows

    def extract_models_from_workflow(
        self, workflow_data: dict, source: str
    ) -> list[ModelReference]:
        """Extract model references from a single workflow.

        Supports two workflow formats:
        1. Old format: {"nodes": [{"type": "...", "widgets_values": [...]}]}
        2. API format: {"node_id": {"class_type": "...", "inputs": {...}}}
        """
        models = []

        # Check if this is the old format (has "nodes" array)
        if "nodes" in workflow_data and isinstance(workflow_data["nodes"], list):
            models.extend(self._extract_from_nodes_format(workflow_data, source))

        # Check if this is the API format (dict with node IDs as keys)
        # API format nodes have "class_type" and "inputs" keys
        else:
            models.extend(self._extract_from_api_format(workflow_data, source))

        return models

    def _extract_from_nodes_format(self, workflow_data: dict, source: str) -> list[ModelReference]:
        """Extract models from old nodes array format."""
        models = []
        nodes = workflow_data.get("nodes", [])

        for node in nodes:
            node_type = node.get("type", "")

            if node_type in MODEL_LOADER_NODES_WIDGETS:
                widgets_values = node.get("widgets_values", [])

                for widget_idx, category in MODEL_LOADER_NODES_WIDGETS[node_type]:
                    if widget_idx < len(widgets_values):
                        value = widgets_values[widget_idx]

                        # Skip non-string values or special values
                        if not isinstance(value, str):
                            continue
                        if value.lower() in ("none", "default", "auto", ""):
                            continue

                        models.append(
                            ModelReference(
                                filename=value,
                                category=category,
                                node_type=node_type,
                                workflow_source=source,
                            )
                        )

        return models

    def _extract_from_api_format(self, workflow_data: dict, source: str) -> list[ModelReference]:
        """Extract models from API format (node IDs as keys)."""
        models = []

        for node_id, node_data in workflow_data.items():
            if not isinstance(node_data, dict):
                continue

            # Get class_type (node type in API format)
            class_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {})

            if not class_type or not inputs:
                continue

            if class_type in MODEL_LOADER_NODES_INPUTS:
                for input_key, category in MODEL_LOADER_NODES_INPUTS[class_type]:
                    value = inputs.get(input_key)

                    # Skip non-string values or special values
                    if not isinstance(value, str):
                        continue
                    if value.lower() in ("none", "default", "auto", ""):
                        continue

                    models.append(
                        ModelReference(
                            filename=value,
                            category=category,
                            node_type=class_type,
                            workflow_source=source,
                        )
                    )

        return models

    def extract_node_types_from_workflow(self, workflow_data: dict, source: str) -> set[str]:
        """Extract all node types (class_types) from a workflow.

        Supports two workflow formats:
        1. Old format: {"nodes": [{"type": "..."}]}
        2. API format: {"node_id": {"class_type": "..."}}
        """
        node_types: set[str] = set()

        # Check if this is the old format (has "nodes" array)
        if "nodes" in workflow_data and isinstance(workflow_data["nodes"], list):
            for node in workflow_data["nodes"]:
                node_type = node.get("type", "")
                if node_type:
                    node_types.add(node_type)
        else:
            # API format (dict with node IDs as keys)
            for node_id, node_data in workflow_data.items():
                if isinstance(node_data, dict):
                    class_type = node_data.get("class_type", "")
                    if class_type:
                        node_types.add(class_type)

        return node_types

    def identify_required_custom_nodes(
        self, node_types: set[str], source: str
    ) -> tuple[dict[str, CustomNodeReference], set[str]]:
        """Identify which custom node packages are required for the given node types.

        Returns:
            Tuple of (required_packages dict, unknown_node_types set)
        """
        required_packages: dict[str, CustomNodeReference] = {}
        unknown_nodes: set[str] = set()

        known_custom_nodes = self.known_nodes_db.get_all_known_node_types()

        for node_type in node_types:
            # Skip built-in nodes
            if node_type in BUILTIN_NODE_TYPES:
                continue

            # Look up in known nodes database
            package_info = self.known_nodes_db.lookup_node(node_type)

            if package_info:
                package_name = package_info["package_name"]
                if package_name not in required_packages:
                    required_packages[package_name] = CustomNodeReference(
                        package_name=package_name,
                        url=package_info["url"],
                        description=package_info["description"],
                        node_types=[node_type],
                        pip_packages=package_info.get("pip_packages", []),
                        workflow_sources=[source],
                    )
                else:
                    # Add this node type if not already tracked
                    if node_type not in required_packages[package_name].node_types:
                        required_packages[package_name].node_types.append(node_type)
                    # Add source if not already tracked
                    if source not in required_packages[package_name].workflow_sources:
                        required_packages[package_name].workflow_sources.append(source)
            elif node_type not in known_custom_nodes:
                # Node type is not built-in and not in known_nodes.yml
                unknown_nodes.add(node_type)

        return required_packages, unknown_nodes

    def resolve_model_url(self, model: ModelReference) -> bool:
        """Try to resolve URL for a model using available resolvers."""
        for resolver_name, resolver in self.resolvers:
            if self.verbose:
                print(f"    Trying {resolver_name}...")

            if resolver_name == "known_db":
                result = resolver.lookup(model.filename, model.category)
            else:
                result = resolver.search(model.filename, model.category)

            if result:
                model.url = result.get("url")
                model.description = result.get("description")
                if self.verbose:
                    print(f"    Found via {resolver_name}: {model.url[:50]}...")
                return True

        return False

    def scan(self, sources: list[str] | None = None) -> ScanResult:
        """Scan workflows and resolve model URLs and custom node requirements."""
        result = ScanResult()

        if sources is None:
            sources = ["local", "database"]

        # Collect workflows from all sources
        all_workflows = []

        if "local" in sources:
            if self.verbose:
                print("Scanning local workflows...")
            all_workflows.extend(self.scan_local_workflows())

        if "database" in sources:
            if self.verbose:
                print("Scanning database workflows...")
            all_workflows.extend(self.scan_database_workflows())

        result.workflows_scanned = len(all_workflows)

        if self.verbose:
            print(f"\nFound {len(all_workflows)} workflows")

        # Extract model references and node types
        all_models: set[ModelReference] = set()

        for source, workflow_data in all_workflows:
            # Extract models
            models = self.extract_models_from_workflow(workflow_data, source)
            all_models.update(models)

            # Extract node types (if enabled)
            if self.scan_nodes:
                node_types = self.extract_node_types_from_workflow(workflow_data, source)
                result.nodes_found.update(node_types)

                # Identify required custom nodes
                required_packages, unknown = self.identify_required_custom_nodes(node_types, source)

                # Merge into result
                for pkg_name, pkg_ref in required_packages.items():
                    if pkg_name not in result.custom_nodes_required:
                        result.custom_nodes_required[pkg_name] = pkg_ref
                    else:
                        # Merge node types and sources
                        existing = result.custom_nodes_required[pkg_name]
                        for nt in pkg_ref.node_types:
                            if nt not in existing.node_types:
                                existing.node_types.append(nt)
                        for src in pkg_ref.workflow_sources:
                            if src not in existing.workflow_sources:
                                existing.workflow_sources.append(src)

                result.unknown_nodes.update(unknown)

        if self.verbose:
            print(f"Found {len(all_models)} unique model references")
            if self.scan_nodes:
                print(f"Found {len(result.nodes_found)} unique node types")
                print(f"Required custom node packages: {len(result.custom_nodes_required)}")
                if result.unknown_nodes:
                    print(f"Unknown node types: {len(result.unknown_nodes)}")

        # Group models by category
        for model in all_models:
            if model.category not in result.models_found:
                result.models_found[model.category] = []
            result.models_found[model.category].append(model)

        # Resolve URLs for each model
        if self.verbose:
            print("\nResolving model URLs...")

        for category, models in result.models_found.items():
            for model in models:
                if self.verbose:
                    print(f"  Resolving: {model.filename} ({category})")

                if self.resolve_model_url(model):
                    if category not in result.resolved_models:
                        result.resolved_models[category] = []
                    result.resolved_models[category].append(model)
                else:
                    if category not in result.unresolved_models:
                        result.unresolved_models[category] = []
                    result.unresolved_models[category].append(model)
                    if self.verbose:
                        print(f"    Could not resolve URL for {model.filename}")

        return result


class ModelsYmlUpdater:
    """Updates models.yml with new model entries."""

    def __init__(self, models_yml_path: Path = MODELS_YML_PATH):
        self.models_yml_path = models_yml_path
        self.existing_models: dict[str, list[dict]] = {}
        self._load()

    def _load(self) -> None:
        """Load existing models.yml."""
        if not self.models_yml_path.exists():
            return

        with open(self.models_yml_path) as f:
            data = yaml.safe_load(f) or {}

        for category, models in data.items():
            if isinstance(models, list):
                self.existing_models[category] = models

    def get_existing_filenames(self, category: str) -> set[str]:
        """Get set of existing filenames in a category."""
        filenames = set()
        for model in self.existing_models.get(category, []):
            if isinstance(model, dict) and "name" in model:
                filenames.add(model["name"])
        return filenames

    def add_models(
        self, resolved_models: dict[str, list[ModelReference]], dry_run: bool = False
    ) -> dict[str, list[dict]]:
        """Add resolved models to models.yml structure."""
        added_models: dict[str, list[dict]] = {}

        for category, models in resolved_models.items():
            existing_names = self.get_existing_filenames(category)

            for model in models:
                if model.filename in existing_names:
                    continue

                if not model.url:
                    continue

                new_entry = {
                    "name": model.filename,
                    "url": model.url,
                    "description": model.description or "Auto-discovered from workflow",
                }

                if category not in added_models:
                    added_models[category] = []
                added_models[category].append(new_entry)

                if category not in self.existing_models:
                    self.existing_models[category] = []
                self.existing_models[category].append(new_entry)
                existing_names.add(model.filename)

        return added_models

    def save(self, dry_run: bool = False) -> None:
        """Save updated models.yml."""
        if dry_run:
            return

        # Build output with comments preserved
        output_lines = [
            "# ComfyUI Model Configuration",
            "# This file defines which models to download automatically on first startup",
            "# Models are organized by category matching ComfyUI's directory structure",
            "# Auto-updated by scan-workflows.py",
            "",
        ]

        # Standard category order
        category_order = [
            "checkpoints",
            "vae",
            "unet",
            "clip",
            "loras",
            "controlnet",
            "upscale_models",
        ]

        # Write categories in order, then any remaining
        written_categories = set()

        for category in category_order:
            if category in self.existing_models:
                self._write_category(output_lines, category, self.existing_models[category])
                written_categories.add(category)

        # Write remaining categories
        for category in sorted(self.existing_models.keys()):
            if category not in written_categories:
                self._write_category(output_lines, category, self.existing_models[category])

        with open(self.models_yml_path, "w") as f:
            f.write("\n".join(output_lines))

    def _write_category(self, output_lines: list[str], category: str, models: list[dict]) -> None:
        """Write a category to output lines."""
        output_lines.append(f"{category}:")

        for model in models:
            if isinstance(model, dict):
                output_lines.append(f"  - name: {model.get('name', '')}")
                output_lines.append(f"    url: {model.get('url', '')}")
                if model.get("description"):
                    output_lines.append(f"    description: {model.get('description')}")

        output_lines.append("")


def print_report(
    result: ScanResult, added_models: dict[str, list[dict]], show_nodes: bool = True
) -> None:
    """Print a summary report of the scan."""
    print("\n" + "=" * 60)
    print("  ComfyUI Workflow Model & Node Scanner Report")
    print("=" * 60)

    print(f"\nWorkflows scanned: {result.workflows_scanned}")

    # Model statistics
    total_found = sum(len(models) for models in result.models_found.values())
    total_resolved = sum(len(models) for models in result.resolved_models.values())
    total_unresolved = sum(len(models) for models in result.unresolved_models.values())
    total_added = sum(len(models) for models in added_models.values())

    print("\n📦 MODELS:")
    print(f"  Total models found: {total_found}")
    print(f"  Resolved: {total_resolved}")
    print(f"  Unresolved: {total_unresolved}")
    print(f"  Added to models.yml: {total_added}")

    if added_models:
        print("\n  Models added to models.yml:")
        for category, models in added_models.items():
            print(f"\n    {category}:")
            for model in models:
                print(f"      - {model['name']}")

    if result.unresolved_models:
        print("\n  ⚠️  Unresolved models (manual URL required):")
        for category, models in result.unresolved_models.items():
            print(f"\n    {category}:")
            for model in models:
                print(f"      - {model.filename}")
                print(f"        Source: {model.workflow_source}")
                print(f"        Node: {model.node_type}")

    # Custom node statistics
    if show_nodes:
        print("\n🔌 CUSTOM NODES:")
        print(f"  Total node types found: {len(result.nodes_found)}")
        print(f"  Required custom node packages: {len(result.custom_nodes_required)}")

        if result.custom_nodes_required:
            print("\n  Required custom node packages:")
            for pkg_name, pkg_ref in sorted(result.custom_nodes_required.items()):
                print(f"\n    📦 {pkg_name}")
                print(f"       URL: {pkg_ref.url}")
                print(f"       Description: {pkg_ref.description}")
                if pkg_ref.pip_packages:
                    print(f"       Pip packages: {', '.join(pkg_ref.pip_packages)}")
                print(f"       Used nodes: {', '.join(pkg_ref.node_types[:5])}", end="")
                if len(pkg_ref.node_types) > 5:
                    print(f" (+{len(pkg_ref.node_types) - 5} more)")
                else:
                    print()

        if result.unknown_nodes:
            print(f"\n  ⚠️  Unknown node types ({len(result.unknown_nodes)}):")
            print(
                "     (These may be built-in nodes not in our list, or custom nodes not in known_nodes.yml)"
            )
            for node_type in sorted(result.unknown_nodes)[:20]:
                print(f"       - {node_type}")
            if len(result.unknown_nodes) > 20:
                print(f"       ... and {len(result.unknown_nodes) - 20} more")

    print("\n" + "=" * 60)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scan ComfyUI workflows for required models and custom nodes"
    )
    parser.add_argument(
        "--source",
        choices=["local", "database", "all"],
        default="all",
        help="Workflow source to scan (default: all)",
    )
    parser.add_argument(
        "--workflow",
        type=Path,
        help="Scan a specific workflow file",
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=DEFAULT_WORKFLOWS_DIR,
        help=f"Directory containing local workflow files (default: {DEFAULT_WORKFLOWS_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without modifying models.yml",
    )
    parser.add_argument(
        "--civitai",
        action="store_true",
        help="Enable CivitAI API search (requires CIVITAI_API_KEY)",
    )
    parser.add_argument(
        "--searxng",
        action="store_true",
        help="Enable SearXNG web search as fallback",
    )
    parser.add_argument(
        "--skip-nodes",
        action="store_true",
        help="Skip custom node detection (only scan for models)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    scan_nodes = not args.skip_nodes

    # Determine sources
    if args.workflow:
        # Scan single workflow file
        sources = ["local"]
        workflows_dir = args.workflow.parent
    else:
        sources = ["local", "database"] if args.source == "all" else [args.source]
        workflows_dir = args.workflows_dir

    # Initialize scanner
    scanner = WorkflowScanner(
        workflows_dir=workflows_dir,
        use_huggingface=True,
        use_civitai=args.civitai,
        use_searxng=args.searxng,
        scan_nodes=scan_nodes,
        verbose=args.verbose,
    )

    # If scanning single workflow, override the scan method
    if args.workflow:
        try:
            with open(args.workflow) as f:
                workflow_data = json.load(f)
            all_workflows = [(str(args.workflow), workflow_data)]

            # Create custom scan result
            result = ScanResult()
            result.workflows_scanned = 1

            all_models: set[ModelReference] = set()
            for source, wf_data in all_workflows:
                models = scanner.extract_models_from_workflow(wf_data, source)
                all_models.update(models)

                # Extract node types (if enabled)
                if scan_nodes:
                    node_types = scanner.extract_node_types_from_workflow(wf_data, source)
                    result.nodes_found.update(node_types)
                    required_packages, unknown = scanner.identify_required_custom_nodes(
                        node_types, source
                    )
                    for pkg_name, pkg_ref in required_packages.items():
                        if pkg_name not in result.custom_nodes_required:
                            result.custom_nodes_required[pkg_name] = pkg_ref
                    result.unknown_nodes.update(unknown)

            for model in all_models:
                if model.category not in result.models_found:
                    result.models_found[model.category] = []
                result.models_found[model.category].append(model)

            for category, models in result.models_found.items():
                for model in models:
                    if scanner.resolve_model_url(model):
                        if category not in result.resolved_models:
                            result.resolved_models[category] = []
                        result.resolved_models[category].append(model)
                    else:
                        if category not in result.unresolved_models:
                            result.unresolved_models[category] = []
                        result.unresolved_models[category].append(model)

        except (json.JSONDecodeError, OSError) as e:
            print(f"Error reading workflow file: {e}")
            return 1
    else:
        # Normal scan
        result = scanner.scan(sources)

    # Update models.yml
    updater = ModelsYmlUpdater()
    added_models = updater.add_models(result.resolved_models, dry_run=args.dry_run)

    if not args.dry_run:
        updater.save()

    # Print report
    print_report(result, added_models, show_nodes=scan_nodes)

    if args.dry_run:
        print("\n[DRY RUN] No changes were made to models.yml")

    # Return non-zero if there are unresolved models or required custom nodes
    has_issues = bool(result.unresolved_models) or bool(result.custom_nodes_required)
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
