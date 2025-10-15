#!/usr/bin/env python3
"""
Script para generar claves secretas seguras para el sistema ERP.
Ejecuta este script y copia las claves generadas a tu archivo .env
"""

import secrets

def generate_secret_key(length=50):
    """Genera una clave secreta criptográficamente segura."""
    return secrets.token_urlsafe(length)

def main():
    print("=" * 70)
    print("GENERADOR DE CLAVES SECRETAS - SISTEMA ERP")
    print("=" * 70)
    print("\n⚠️  IMPORTANTE: Estas claves son SENSIBLES y ÚNICAS")
    print("   - NO las compartas públicamente")
    print("   - NO las subas a Git")
    print("   - Guárdalas en un gestor de contraseñas seguro")
    print("   - Úsalas SOLO para tu instancia del sistema\n")
    
    print("Generando claves seguras...\n")
    
    # Generar claves
    django_secret = generate_secret_key(50)
    jwt_signing = generate_secret_key(50)
    
    print("📋 Copia estas líneas a tu archivo .env:\n")
    print("-" * 70)
    print(f"DJANGO_SECRET_KEY={django_secret}")
    print(f"JWT_SIGNING_KEY={jwt_signing}")
    print("-" * 70)
    
    print("\n✅ Claves generadas exitosamente!")
    print("\nPróximos pasos:")
    print("1. Crea el archivo backend/.env si no existe")
    print("2. Copia las líneas de arriba al archivo .env")
    print("3. Completa las demás variables según ENV_EXAMPLE.txt")
    print("4. Verifica que .env esté en .gitignore")
    print("5. En producción, usa Secret Manager de tu proveedor cloud\n")
    
    # Información adicional
    print("💡 Información de las claves generadas:")
    print(f"   - Longitud: 50 caracteres (base64 URL-safe)")
    print(f"   - Entropía: ~300 bits de seguridad")
    print(f"   - Método: secrets.token_urlsafe() - criptográficamente seguro")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()

