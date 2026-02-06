#!/bin/sh
# Minimal udhcpc helper for Kuvoz WPS Wi-Fi
# Applies IP, default route, and DNS for the interface.

mask2cidr() {
  n=0
  oldifs=$IFS
  IFS=.
  set -- $1
  IFS=$oldifs
  for x in "$@"; do
    case "$x" in
      255) n=$((n+8)) ;;
      254) n=$((n+7)) ;;
      252) n=$((n+6)) ;;
      248) n=$((n+5)) ;;
      240) n=$((n+4)) ;;
      224) n=$((n+3)) ;;
      192) n=$((n+2)) ;;
      128) n=$((n+1)) ;;
      0) ;;
      *) echo "" ; return 1 ;;
    esac
  done
  echo "$n"
}

IFACE="${interface:-}"
ACTION="${1:-}"

if [ -z "$IFACE" ] || [ -z "$ACTION" ]; then
  exit 0
fi

case "$ACTION" in
  bound|renew)
    if [ -n "${ip:-}" ]; then
      PREFIX=""
      if [ -n "${subnet:-}" ]; then
        case "$subnet" in
          *.*) PREFIX="$(mask2cidr "$subnet")" ;;
          *) PREFIX="$subnet" ;;
        esac
      fi
      if [ -z "$PREFIX" ]; then
        PREFIX="24"
      fi
      ip addr flush dev "$IFACE" 2>/dev/null || true
      ip addr add "$ip/$PREFIX" dev "$IFACE" 2>/dev/null || true
      ip link set "$IFACE" up 2>/dev/null || true
    fi

    if [ -n "${router:-}" ]; then
      set -- $router
      GW="$1"
      if [ -n "$GW" ]; then
        if ! ip route show default dev "$IFACE" | grep -q '^default'; then
          if ip route show default | grep -q '^default'; then
            ip route add default via "$GW" dev "$IFACE" metric 200 2>/dev/null || true
          else
            ip route add default via "$GW" dev "$IFACE" metric 100 2>/dev/null || true
          fi
        fi
      fi
    fi

    if [ -n "${dns:-}" ]; then
      : > /etc/resolv.conf
      for d in $dns; do
        echo "nameserver $d" >> /etc/resolv.conf
      done
    fi
    ;;
  deconfig)
    ip addr flush dev "$IFACE" 2>/dev/null || true
    ;;
esac

exit 0
