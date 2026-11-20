#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddns-pilahito — actualiza registros DNS de Cloudflare cuando cambia la IP pública.

Pensado para cuando reinicias el router (o el operador te da otra IP): en vez
de entrar a mano en Cloudflare, este script mira la IP pública, la compara con
la que ya está puesta en los registros A y la actualiza si hace falta.

Configuración (una sola vez): ~/.config/ddns-pilahito.json
{
  "token": "TOKEN_CLOUDFLARE_CON_PERMISO_DNS_EDIT",
  "zona": "pilahito.org",
  "registros": ["mc.pilahito.org", "amp.pilahito.org"],
  "proxied": false
}

Uso:
    ddns-pilahito           actualiza si hace falta
    ddns-pilahito --dry-run  solo dice lo que haría
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG = Path.home() / ".config" / "ddns-pilahito.json"
ESTADO = Path.home() / ".local" / "state" / "ddns-pilahito.json"
API = "https://api.cloudflare.com/client/v4"


def log(msg):
    print(msg, flush=True)


def ip_publica():
    for url, patron in (
        ("https://1.1.1.1/cdn-cgi/trace", "ip="),
        ("https://api.ipify.org", ""),
    ):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                texto = r.read().decode().strip()
            if patron:
                for linea in texto.splitlines():
                    if linea.startswith(patron):
                        return linea[len(patron):].strip()
            else:
                return texto
        except Exception:
            continue
    raise SystemExit("no pude averiguar la IP pública")


def cf(method, ruta, token, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(
        API + ruta, data=datos, method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        cuerpo_error = e.read().decode("utf-8", "replace")
        raise SystemExit(f"Cloudflare respondió {e.code}: {cuerpo_error[:200]}")


def main():
    dry = "--dry-run" in sys.argv
    if not CONFIG.exists():
        raise SystemExit(f"falta {CONFIG} (token de Cloudflare con permiso DNS:Edit)")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    token = cfg.get("token", "").strip()
    if not token:
        raise SystemExit("el token está vacío en la configuración")
    zona = cfg.get("zona", "pilahito.org")
    registros = cfg.get("registros") or []
    proxied = bool(cfg.get("proxied", False))

    ip = ip_publica()
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    try:
        estado = json.loads(ESTADO.read_text(encoding="utf-8"))
    except Exception:
        estado = {}

    if estado.get("ip") == ip:
        log(f"sin cambios: la IP sigue siendo {ip}")
        return 0

    log(f"IP pública: {ip} (antes: {estado.get('ip', 'desconocida')})")
    zonas = cf("GET", f"/zones?name={zona}", token).get("result") or []
    if not zonas:
        raise SystemExit(f"el token no ve la zona {zona} (¿le falta permiso Zone:Read?)")
    zona_id = zonas[0]["id"]

    cambios = 0
    for nombre in registros:
        existentes = cf("GET", f"/zones/{zona_id}/dns_records?name={nombre}&type=A", token).get("result") or []
        if existentes:
            registro = existentes[0]
            if registro["content"] == ip:
                log(f"  {nombre}: ya apunta a {ip}")
                continue
            log(f"  {nombre}: {registro['content']} -> {ip}" + (" (simulación)" if dry else ""))
            if not dry:
                cf("PATCH", f"/zones/{zona_id}/dns_records/{registro['id']}", token,
                   {"content": ip, "proxied": proxied})
                cambios += 1
        else:
            log(f"  {nombre}: no existe, se crea -> {ip}" + (" (simulación)" if dry else ""))
            if not dry:
                cf("POST", f"/zones/{zona_id}/dns_records", token,
                   {"type": "A", "name": nombre, "content": ip, "ttl": 120, "proxied": proxied})
                cambios += 1

    if not dry:
        estado["ip"] = ip
        ESTADO.write_text(json.dumps(estado, indent=1), encoding="utf-8")
    log(f"listo: {cambios} registro(s) actualizados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
