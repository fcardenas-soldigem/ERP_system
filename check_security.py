#!/usr/bin/env python3
"""
Script de verificación de seguridad para el sistema ERP.
Ejecuta este script para verificar que la configuración de seguridad esté correcta.
"""

import os
import sys
from pathlib import Path

def check_env_file():
    """Verifica que exista el archivo .env"""
    env_path = Path(__file__).parent / "backend" / ".env"
    if not env_path.exists():
        return False, ".env no encontrado en backend/"
    return True, ".env existe"

def check_gitignore():
    """Verifica que .env esté en .gitignore"""
    gitignore_path = Path(__file__).parent / ".gitignore"
    if not gitignore_path.exists():
        return False, ".gitignore no encontrado"
    
    with open(gitignore_path, 'r') as f:
        content = f.read()
        if '.env' in content or '*.env' in content:
            return True, ".env está en .gitignore"
        else:
            return False, ".env NO está en .gitignore (PELIGRO)"

def check_env_variables():
    """Verifica que las variables críticas estén configuradas"""
    env_path = Path(__file__).parent / "backend" / ".env"
    if not env_path.exists():
        return False, "No se puede verificar (archivo .env no existe)"
    
    required_vars = [
        'DJANGO_SECRET_KEY',
        'JWT_SIGNING_KEY',
        'APIS_NET_PE_TOKEN',
        'DJANGO_ALLOWED_HOSTS',
        'CORS_ALLOWED_ORIGINS',
    ]
    
    missing = []
    weak = []
    
    with open(env_path, 'r') as f:
        content = f.read()
        
        for var in required_vars:
            if var not in content:
                missing.append(var)
            else:
                # Check si tiene valores de ejemplo
                if var == 'DJANGO_SECRET_KEY' and 'tu-clave-secreta' in content:
                    weak.append(var)
                elif var == 'JWT_SIGNING_KEY' and 'otra-clave-diferente' in content:
                    weak.append(var)
                elif var == 'APIS_NET_PE_TOKEN' and 'tu-token-de-apis' in content:
                    weak.append(var)
    
    if missing:
        return False, f"Variables faltantes: {', '.join(missing)}"
    if weak:
        return False, f"Variables con valores de ejemplo: {', '.join(weak)}"
    
    return True, "Todas las variables críticas están configuradas"

def check_dockerfile_user():
    """Verifica que los Dockerfiles usen usuario no-root"""
    backend_dockerfile = Path(__file__).parent / "backend" / "Dockerfile"
    frontend_dockerfile = Path(__file__).parent / "frontend" / "Dockerfile"
    
    results = []
    
    # Check backend
    if backend_dockerfile.exists():
        with open(backend_dockerfile, 'r') as f:
            content = f.read()
            if 'USER appuser' in content or 'USER 1000' in content:
                results.append(("✅", "Backend Dockerfile usa usuario no-root"))
            else:
                results.append(("❌", "Backend Dockerfile NO usa usuario no-root"))
    
    # Check frontend
    if frontend_dockerfile.exists():
        with open(frontend_dockerfile, 'r') as f:
            content = f.read()
            if 'USER nginx' in content:
                results.append(("✅", "Frontend Dockerfile usa usuario no-root"))
            else:
                results.append(("❌", "Frontend Dockerfile NO usa usuario no-root"))
    
    return results

def check_nginx_headers():
    """Verifica que nginx.conf tenga headers de seguridad"""
    nginx_conf = Path(__file__).parent / "frontend" / "nginx.conf"
    
    if not nginx_conf.exists():
        return False, "nginx.conf no encontrado"
    
    required_headers = [
        'Content-Security-Policy',
        'X-Frame-Options',
        'X-Content-Type-Options',
        'Referrer-Policy',
    ]
    
    with open(nginx_conf, 'r') as f:
        content = f.read()
        
    missing = [h for h in required_headers if h not in content]
    
    if missing:
        return False, f"Headers faltantes: {', '.join(missing)}"
    
    return True, "Headers de seguridad configurados"

def check_settings_security():
    """Verifica configuraciones de seguridad en settings.py"""
    settings_path = Path(__file__).parent / "backend" / "config" / "settings.py"
    
    if not settings_path.exists():
        return [], "settings.py no encontrado"
    
    with open(settings_path, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check SECRET_KEY
    if "SECRET_KEY = 'Rafaella" in content:
        checks.append(("❌", "SECRET_KEY todavía hardcodeado"))
    elif "SECRET_KEY = os.getenv" in content:
        checks.append(("✅", "SECRET_KEY usa variable de entorno"))
    
    # Check CORS
    if "CORS_ALLOW_ALL_ORIGINS = True" in content:
        checks.append(("❌", "CORS_ALLOW_ALL_ORIGINS = True (INSEGURO)"))
    elif "CORS_ALLOWED_ORIGINS" in content:
        checks.append(("✅", "CORS_ALLOWED_ORIGINS configurado correctamente"))
    
    # Check JWT
    if "ACCESS_TOKEN_LIFETIME = timedelta(days=1)" in content:
        checks.append(("❌", "JWT token muy largo (1 día)"))
    elif "ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)" in content:
        checks.append(("✅", "JWT token seguro (15 minutos)"))
    
    # Check cookies
    if "SESSION_COOKIE_SECURE" in content:
        checks.append(("✅", "Cookies seguras configuradas"))
    else:
        checks.append(("⚠️", "Cookies seguras no encontradas"))
    
    # Check HSTS
    if "SECURE_HSTS_SECONDS" in content:
        checks.append(("✅", "HSTS configurado"))
    else:
        checks.append(("⚠️", "HSTS no encontrado"))
    
    return checks, "Verificación completada"

def main():
    print("=" * 70)
    print("VERIFICACIÓN DE SEGURIDAD - SISTEMA ERP")
    print("=" * 70)
    print()
    
    all_passed = True
    
    # 1. Check archivo .env
    print("1️⃣  Archivo .env")
    passed, msg = check_env_file()
    print(f"   {'✅' if passed else '❌'} {msg}")
    if not passed:
        all_passed = False
    print()
    
    # 2. Check .gitignore
    print("2️⃣  .gitignore")
    passed, msg = check_gitignore()
    print(f"   {'✅' if passed else '❌'} {msg}")
    if not passed:
        all_passed = False
    print()
    
    # 3. Check variables de entorno
    print("3️⃣  Variables de entorno críticas")
    passed, msg = check_env_variables()
    print(f"   {'✅' if passed else '❌'} {msg}")
    if not passed:
        all_passed = False
    print()
    
    # 4. Check Dockerfiles
    print("4️⃣  Dockerfiles (usuario no-root)")
    results = check_dockerfile_user()
    for icon, msg in results:
        print(f"   {icon} {msg}")
        if icon == "❌":
            all_passed = False
    print()
    
    # 5. Check Nginx headers
    print("5️⃣  Headers de seguridad Nginx")
    passed, msg = check_nginx_headers()
    print(f"   {'✅' if passed else '❌'} {msg}")
    if not passed:
        all_passed = False
    print()
    
    # 6. Check settings.py
    print("6️⃣  Configuración Django (settings.py)")
    checks, msg = check_settings_security()
    for icon, check_msg in checks:
        print(f"   {icon} {check_msg}")
        if icon == "❌":
            all_passed = False
    print()
    
    # Resultado final
    print("=" * 70)
    if all_passed:
        print("✅ TODAS LAS VERIFICACIONES PASARON")
        print("   Tu sistema tiene una configuración de seguridad sólida.")
        print("   Calificación estimada: 8/10")
        print()
        print("📋 Próximos pasos:")
        print("   - Asegúrate de usar Secret Manager en producción")
        print("   - Activa HSTS en nginx cuando tengas HTTPS")
        print("   - Configura rate limiting")
        print("   - Mueve la DB a una red privada")
        return 0
    else:
        print("⚠️  ALGUNAS VERIFICACIONES FALLARON")
        print("   Revisa los items marcados con ❌ arriba.")
        print()
        print("📋 Acciones requeridas:")
        print("   1. Ejecuta: python3 generate_secrets.py")
        print("   2. Crea backend/.env con las claves generadas")
        print("   3. Completa todas las variables según ENV_EXAMPLE.txt")
        print("   4. Verifica que .env esté en .gitignore")
        return 1
    
    print("=" * 70)

if __name__ == "__main__":
    sys.exit(main())

