"""OSIRIS komut satırı arayüzü."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option("0.1.0", prog_name="osiris")
def main() -> None:
    """OSIRIS — Açık Kaynak İstihbarat Platformu."""


@main.command()
def status() -> None:
    """Sistem durumunu göster."""
    console.print("[bold green]OSIRIS[/bold green] — durum: [yellow]Faz 1 (temel altyapı)[/yellow]")


@main.command()
@click.option("--plugins-dir", default="plugins", help="Plugin dizini")
def plugins(plugins_dir: str) -> None:
    """Yüklü plugin'leri listele."""
    from osiris_collector.manager import CollectorManager

    manager = CollectorManager(plugins_dir=plugins_dir)
    count = manager.load_plugins()
    console.print(f"[bold]{count}[/bold] plugin yüklendi:")
    for pid, plugin in manager.plugins.items():
        console.print(f"  [cyan]{pid}[/cyan] — {plugin.name} ({plugin.network_type})")


@main.command()
@click.argument("plugin_id")
@click.option("--config", default="{}", help="Görev yapılandırması (JSON)")
def collect(plugin_id: str, config: str) -> None:
    """Tek bir koleksiyon görevi çalıştır."""
    import json

    from osiris_collector.manager import CollectorManager

    try:
        cfg = json.loads(config)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Geçersiz JSON config:[/red] {exc}")
        raise SystemExit(2) from exc
    if not isinstance(cfg, dict):
        console.print("[red]config bir JSON objesi olmalı[/red]")
        raise SystemExit(2)
    manager = CollectorManager()
    manager.load_plugins()
    try:
        result = manager.run_collection(plugin_id, cfg)
    except KeyError:
        console.print(f"[red]Plugin bulunamadı:[/red] {plugin_id}")
        raise SystemExit(1) from None
    if result.success:
        console.print(f"[green]{len(result.items)}[/green] öğe toplandı")
    else:
        console.print(f"[red]Hata:[/red] {result.error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
