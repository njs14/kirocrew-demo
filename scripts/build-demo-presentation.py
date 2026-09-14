#!/usr/bin/env python3
"""Rebuild a committed presentation recipe into a fresh portable directory.

Only the Python standard library is required. This command reads reviewed media
and public receipts; it never connects to AWS, records a screen, or runs a demo.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / "config/presentation-native.json"
SPEC = importlib.util.spec_from_file_location("native_presentation", ROOT / "scripts/build-native-control-presentation.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

FIELDS = {"schema_version", "edition", "description", "manifests", "receipts", "admin_build", "diagram_build",
          "pending_controls", "limitations", "recording_coverage", "supporting_inputs", "input_sha256", "accepted_reference"}


def project_file(value):
    if (not isinstance(value, str) or not value or "\\" in value or value.startswith("/")
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("Recipe inputs must be unambiguous project-relative paths")
    return builder.safe_file(ROOT / value)


def load_recipe(path=DEFAULT_RECIPE):
    path = Path(path)
    recipe_path = builder.safe_file(path if path.is_absolute() else ROOT / path)
    if recipe_path.stat().st_size > 1_000_000:
        raise ValueError("Presentation recipe exceeds 1 MB")
    recipe = json.loads(recipe_path.read_bytes())
    if not isinstance(recipe, dict) or recipe.get("schema_version") != 1 or set(recipe) != FIELDS:
        raise ValueError("Expected a schema_version 1 presentation recipe with the documented fields")
    if not isinstance(recipe["edition"], str) or not re.fullmatch(r"[A-Za-z0-9_-]+", recipe["edition"]):
        raise ValueError("Invalid presentation edition name")
    for name in ("manifests", "receipts", "pending_controls", "limitations", "supporting_inputs"):
        values = recipe[name]
        if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values) or len(values) != len(set(values)):
            raise ValueError(f"{name} must be a list of unique strings")
    if not recipe["manifests"]:
        raise ValueError("A presentation recipe needs at least one processed manifest")
    coverage = recipe["recording_coverage"]
    if (not isinstance(coverage, dict)
            or any(not isinstance(key, str) or value not in builder.RECORDING_COVERAGE for key, value in coverage.items())):
        raise ValueError("Invalid recording_coverage mapping")
    paths = recipe["manifests"] + recipe["receipts"] + recipe["supporting_inputs"]
    for field in ("admin_build", "diagram_build"):
        if recipe[field] is not None:
            paths.append(recipe[field])
    bindings = recipe["input_sha256"]
    if not isinstance(bindings, dict) or set(bindings) != set(paths):
        raise ValueError("input_sha256 must bind every recipe input exactly once")
    for relative, expected in bindings.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid recipe input SHA-256")
        actual = builder.sha(project_file(relative).read_bytes())
        if actual != expected:
            raise ValueError(f"Recipe input changed: {relative}; review it and update its input_sha256 binding")
    return recipe


def receipt_dependencies(receipt):
    """Follow only the two declared public presentation-receipt contracts."""
    if not isinstance(receipt, dict):
        return []
    if receipt.get("kind") == "managed_native_presentation":
        return receipt.get("receipts", []) + receipt.get("screenshots", [])
    if receipt.get("kind") == "native_managed_host_media_review":
        frames_binding = receipt.get("bindings", {}).get("keyframeProvenance")
        if not isinstance(frames_binding, dict):
            raise ValueError("Host media review requires keyframe provenance")
        frames_path = project_file(frames_binding["path"])
        frames = json.loads(builder.validate_hash(frames_path, frames_binding, "keyframe provenance"))
        if frames.get("manifestSha256") != receipt["bindings"]["outputManifest"]["sha256"]:
            raise ValueError("Keyframes must bind the reviewed processed manifest")
        dependencies = [frames_binding, *frames["keyframes"]]
        if any(not item["path"].startswith("output/") or any(part in {".build", "raw"} for part in Path(item["path"]).parts)
               for item in dependencies):
            raise ValueError("Host keyframes must be public output assets")
        return dependencies
    if receipt.get("kind") != "managed_host_native_evidence_index":
        return []
    if receipt.get("schema_version") != 1 or not isinstance(receipt.get("takes"), list):
        raise ValueError("Expected a schema_version 1 managed host evidence index")
    dependencies = [receipt.get(key) for key in ("host_state_snapshots", "findings", "public_review")]
    for take in receipt["takes"]:
        if not isinstance(take, dict) or not isinstance(take.get("corroboration"), list):
            raise ValueError("Invalid managed host take dependencies")
        dependencies.append(take.get("review"))
        dependencies.extend(take["corroboration"])
    if not all(isinstance(item, dict) and isinstance(item.get("path"), str) for item in dependencies):
        raise ValueError("Managed host evidence needs explicit public dependency bindings")
    if any(any(part in {".build", "raw"} for part in Path(item["path"]).parts)
           or Path(item["path"]).name == "demo.local.json" for item in dependencies):
        raise ValueError("Managed host presentation dependencies cannot include private state")
    return dependencies


def check_assets(recipe):
    """Read every media/admin dependency named by the hash-bound recipe."""
    checked = set()

    def check(path, metadata):
        builder.validate_hash(path, metadata, path.name)
        checked.add(path.relative_to(ROOT).as_posix())

    scenes = 0
    for relative in recipe["manifests"]:
        path = project_file(relative)
        manifest = json.loads(path.read_bytes())
        if manifest.get("schemaVersion") != 1 or not manifest.get("scenes"):
            raise ValueError(f"Expected a processed scene manifest: {relative}")
        scenes += len(manifest["scenes"])
        for scene in manifest["scenes"]:
            for metadata in scene.get("media", []) + [scene.get("poster"), scene.get("contactSheet")]:
                if metadata is not None:
                    check(builder.local_asset(metadata.get("url"), path.parent, path.parent), metadata)
        for metadata in manifest.get("evidence", []):
            check(builder.local_asset(metadata.get("url"), path.parent, path.parent), metadata)
    if recipe["admin_build"]:
        admin = json.loads(project_file(recipe["admin_build"]).read_bytes())
        if admin.get("kind") != "native_admin_tour_build":
            raise ValueError("Expected a native admin tour build")
        for item in admin.get("outputs", []) + admin.get("sources", []) + admin.get("screenshots", []):
            check(project_file(item["path"]), item)
    if recipe["diagram_build"]:
        dependency = json.loads(project_file(recipe["diagram_build"]).read_bytes())
        artifact = dependency["artifact"]
        check(project_file(artifact["path"]), artifact)
    for relative in recipe["receipts"]:
        if not relative.endswith(".json"):
            continue
        receipt = json.loads(project_file(relative).read_bytes())
        for item in receipt_dependencies(receipt):
            check(project_file(item["path"]), item)
    return {"recipeInputCount": len(recipe["input_sha256"]), "boundAssetCount": len(checked), "sceneCount": scenes}


def rebuild(recipe, output_dir):
    receipt = builder.build(
        [project_file(path) for path in recipe["manifests"]],
        [project_file(path) for path in recipe["receipts"]],
        project_file(recipe["admin_build"]) if recipe["admin_build"] else None,
        pending_controls=recipe["pending_controls"], limitations=recipe["limitations"],
        recording_coverage=[f"{key}={value}" for key, value in recipe["recording_coverage"].items()],
        diagram_build=project_file(recipe["diagram_build"]) if recipe["diagram_build"] else None,
        output_dir=output_dir)
    export = Path(output_dir).absolute()
    if "/README.txt" in receipt["serveFiles"] or (export / "README.txt").exists() or (export / "README.txt").is_symlink():
        raise ValueError("Playback README route collides with an existing export artifact; existing bytes were preserved")
    scope = "Presentation playback export only. Run the complete project skill and live setup from the project checkout."
    readme = ("KiroCrew presentation playback export\n\n" + scope + "\n\n"
              "This folder contains the recorded presentation, its explicitly bound media and evidence, and the loopback preview server. "
              "It contains no live runtime, AWS configuration, credentials, or raw recordings.\n\n"
              "From this directory, run:\n"
              "python3 scripts/serve-recorded-demos.py --build kirocrew-native-controls-build.json --port 5612\n\n"
              "Open http://127.0.0.1:5612/ in a browser. Direct file:// playback does not provide the artifact routes.\n\n"
              "The presentation includes snapshots of the project skill and setup guides for reference. "
              "Their transitive documentation and executable setup dependencies are not packaged as a live project here. "
              "Use the complete private project checkout to follow those links or run $kirocrew-demo.\n")
    builder.write_atomic(export / "README.txt", readme)
    receipt["serveFiles"]["/README.txt"] = {"path": "README.txt", "bytes": len(readme.encode()), "sha256": builder.sha(readme.encode())}
    receipt["portableExport"]["scope"] = scope
    receipt["portableExport"]["transitiveLiveSetupLinksIncluded"] = False
    builder.write_atomic(export / builder.BUILD.name, json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE, help="Project-relative or absolute path to a recipe inside this project.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Read-only validation of recipe input and asset hashes; does not build or grant a new review verdict.")
    action.add_argument("--output-dir", type=Path, help="Fresh export directory. Existing directories are never replaced.")
    args = parser.parse_args()
    try:
        recipe = load_recipe(args.recipe)
        result = {"edition": recipe["edition"], **check_assets(recipe)}
        if args.output_dir is not None:
            receipt = rebuild(recipe, args.output_dir)
            export = args.output_dir.absolute()
            result.update({"exportDirectory": str(export), "buildReceipt": str(export / builder.BUILD.name),
                           "editionSha256": receipt["editionSha256"], "slideCount": receipt["slideCount"],
                           "previewCommand": [sys.executable, str(export / "scripts/serve-recorded-demos.py"),
                                              "--build", str(export / builder.BUILD.name), "--port", "5612"],
                           "playback": "Use the included loopback server; file:// does not provide the artifact routes.",
                           "setupScope": receipt["portableExport"]["scope"],
                           "reviewScope": "A derivative build does not inherit browser or model-council approval."})
        else:
            result["checks"] = "Recipe inputs and referenced asset hashes match. Full build and browser review are separate."
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Presentation build failed: {exc}\n")


if __name__ == "__main__":
    main()
