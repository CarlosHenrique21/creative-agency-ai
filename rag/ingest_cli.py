#!/usr/bin/env python3
"""
CLI for populating the RAG stores from local directories.

Usage:
    # Ingest brand documents
    python -m rag.ingest_cli docs --brand-id ecobottle --dir ./brand_assets/docs

    # Ingest visual references
    python -m rag.ingest_cli images --brand-id ecobottle --dir ./brand_assets/images

    # List ingested assets
    python -m rag.ingest_cli list --brand-id ecobottle

    # Delete all data for a brand
    python -m rag.ingest_cli delete --brand-id ecobottle
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def _print_table(rows: list[tuple[str, str]]) -> None:
    if not rows:
        print("  (empty)")
        return
    w = max(len(r[0]) for r in rows)
    for name, value in rows:
        print(f"  {name:<{w}}  {value}")


def cmd_docs(args: argparse.Namespace) -> None:
    from rag.dependencies import brand_store

    directory = Path(args.dir)
    if not directory.exists():
        print(f"[error] Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)

    print(f"Ingesting documents from '{directory}' → brand_id='{args.brand_id}' ...")
    results = brand_store.ingest_directory(args.brand_id, directory)

    if not results:
        print("[warn] No supported files found. Supported: .pdf .docx .txt .md .json")
        return

    print(f"\nIngested {len(results)} file(s):")
    _print_table([(name, f"{chunks} chunks") for name, chunks in results.items()])
    print(f"\nTotal chunks: {sum(results.values())}")


async def _cmd_images_async(args: argparse.Namespace) -> None:
    from rag.dependencies import visual_store

    directory = Path(args.dir)
    if not directory.exists():
        print(f"[error] Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)

    print(f"Analysing images from '{directory}' → brand_id='{args.brand_id}' ...")
    print("(each image is sent to GPT-4o Vision — this may take a few seconds per image)\n")
    results = await visual_store.ingest_directory(args.brand_id, directory)

    if not results:
        print("[warn] No supported images found. Supported: .jpg .jpeg .png .webp .gif")
        return

    print(f"Analysed and ingested {len(results)} image(s):")
    for name, desc in results.items():
        style = desc.get("style", "?")
        mood = desc.get("mood", "?")
        keywords = ", ".join(desc.get("prompt_keywords", [])[:5])
        print(f"\n  {name}")
        print(f"    style    : {style}")
        print(f"    mood     : {mood}")
        print(f"    keywords : {keywords}")


def cmd_images(args: argparse.Namespace) -> None:
    asyncio.run(_cmd_images_async(args))


def cmd_list(args: argparse.Namespace) -> None:
    from rag.dependencies import brand_store, visual_store

    docs = brand_store.list_files(args.brand_id)
    images = visual_store.list_images(args.brand_id)

    print(f"\nbrand_id: {args.brand_id}")
    print(f"\nDocuments ({len(docs)}):")
    _print_table([(f, "") for f in docs])
    print(f"\nImages ({len(images)}):")
    _print_table([(f, "") for f in images])


def cmd_delete(args: argparse.Namespace) -> None:
    from rag.dependencies import brand_store, visual_store

    confirm = input(f"Delete ALL RAG data for brand_id='{args.brand_id}'? [y/N] ")
    if confirm.lower() != "y":
        print("Aborted.")
        return

    brand_store.delete_brand(args.brand_id)
    visual_store.delete_brand(args.brand_id)
    print(f"Deleted all data for brand_id='{args.brand_id}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Social Media Agency — RAG CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_docs = sub.add_parser("docs", help="Ingest brand documents")
    p_docs.add_argument("--brand-id", required=True)
    p_docs.add_argument("--dir", required=True)

    p_img = sub.add_parser("images", help="Ingest visual reference images")
    p_img.add_argument("--brand-id", required=True)
    p_img.add_argument("--dir", required=True)

    p_list = sub.add_parser("list", help="List ingested assets")
    p_list.add_argument("--brand-id", required=True)

    p_del = sub.add_parser("delete", help="Delete all RAG data for a brand")
    p_del.add_argument("--brand-id", required=True)

    args = parser.parse_args()
    {"docs": cmd_docs, "images": cmd_images, "list": cmd_list, "delete": cmd_delete}[
        args.command
    ](args)


if __name__ == "__main__":
    main()
