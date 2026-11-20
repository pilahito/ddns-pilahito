# ddns-pilahito

**DDNS para Cloudflare** en 120 líneas de Python: cuando tu IP pública cambia,
actualiza los registros DNS A solos. Pensado para los que tenéis servidor en
casa con IP dinámica y un dominio en Cloudflare.

## Cómo funciona

1. Averigua la IP pública (Cloudflare trace, con `ipify` de respaldo).
2. Si es la misma que la última vez → no hace nada (no gasta peticiones).
3. Si cambió → recorre los registros configurados, compara y los actualiza
   (los crea si no existen).

Por eso puede correr cada 5 minutos sin castigar la API: solo llama a
Cloudflare cuando de verdad ha cambiado algo.

## Instalación

```bash
git clone https://github.com/pilahito/ddns-pilahito.git
cd ddns-pilahito
install -m755 ddns-pilahito.py ~/.local/bin/ddns-pilahito

mkdir -p ~/.config
cp config.example.json ~/.config/ddns-pilahito.json
chmod 600 ~/.config/ddns-pilahito.json   # contiene el token
$EDITOR ~/.config/ddns-pilahito.json
```

### Token de Cloudflare

Crea un **API Token** con la plantilla **"Edit zone DNS"**, limitado a tu zona:

- Cloudflare → My Profile → API Tokens → Create Token → *Edit zone DNS*
- Zone Resources: *Include → specific zone → tu dominio*

Ese token **no** sirve para Workers ni para otras zonas: solo DNS de esa zona.

### Automático con systemd (usuario)

```bash
mkdir -p ~/.config/systemd/user
cp packaging/ddns-pilahito.service packaging/ddns-pilahito.timer ~/.config/systemd/user/
# ajusta el ExecStart del .service a la ruta de tu script
systemctl --user daemon-reload
systemctl --user enable --now ddns-pilahito.timer
```

Comprobar:

```bash
systemctl --user list-timers ddns-pilahito.timer
journalctl --user -u ddns-pilahito.service -n 20
```

## Uso manual

```bash
ddns-pilahito            # actualiza si hace falta
ddns-pilahito --dry-run  # solo dice lo que haría
```

Salida típica:

```
IP pública: 203.0.113.10 (antes: 198.51.100.7)
  mc.ejemplo.org: 198.51.100.7 -> 203.0.113.10
  otro.ejemplo.org: no existe, se crea -> 203.0.113.10
listo: 2 registro(s) actualizados
```

## Qué NO hace

- No actualiza zonas que no estén en `registros`.
- No toca registros proxied si los pones con `"proxied": true` (los deja como
  estén, solo cambia el contenido).
- No sirve para IPv6 (solo A). Se puede añadir AAAA fácilmente.

## Licencia

MIT.
