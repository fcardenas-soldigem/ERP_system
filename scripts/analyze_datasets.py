#!/usr/bin/env python3
"""
Script para analizar y validar datasets subidos
Genera reporte de calidad de datos y sugerencias
"""
import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# Agregar el backend al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

DATASETS_DIR = Path(__file__).parent.parent / 'datasets'


def analyze_csv(file_path):
    """Analiza un archivo CSV y retorna estadísticas"""
    try:
        df = pd.read_csv(file_path)
        
        stats = {
            'filename': file_path.name,
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'missing_values': df.isnull().sum().to_dict(),
            'duplicates': df.duplicated().sum(),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB",
            'sample': df.head(3).to_dict('records') if len(df) > 0 else []
        }
        
        # Detectar columnas de fecha
        date_columns = []
        for col in df.columns:
            if 'fecha' in col.lower() or 'date' in col.lower():
                date_columns.append(col)
        stats['date_columns'] = date_columns
        
        # Detectar columnas de ID
        id_columns = []
        for col in df.columns:
            if '_id' in col.lower() or col.lower().endswith('id'):
                id_columns.append(col)
        stats['id_columns'] = id_columns
        
        return stats, None
        
    except Exception as e:
        return None, str(e)


def scan_datasets_folder(folder_name):
    """Escanea una carpeta de datasets"""
    folder_path = DATASETS_DIR / folder_name
    
    if not folder_path.exists():
        return []
    
    results = []
    for file_path in folder_path.glob('*.csv'):
        stats, error = analyze_csv(file_path)
        if stats:
            results.append(stats)
        else:
            results.append({
                'filename': file_path.name,
                'error': error
            })
    
    return results


def check_dataset_requirements():
    """Verifica si hay suficientes datos para cada modelo"""
    requirements = {
        'RFM Segmentation': {
            'folder': 'clientes',
            'min_rows': 50,
            'required_columns': ['cliente_id', 'fecha', 'monto']
        },
        'Churn Prediction': {
            'folder': 'clientes',
            'min_rows': 100,
            'required_columns': ['cliente_id', 'fecha_ultima_compra', 'total_compras']
        },
        'Product Recommendations': {
            'folder': 'transacciones',
            'min_rows': 100,
            'required_columns': ['transaccion_id', 'producto_id']
        },
        'Demand Forecasting': {
            'folder': 'ventas',
            'min_rows': 30,
            'required_columns': ['producto_id', 'fecha', 'cantidad']
        }
    }
    
    results = {}
    for model_name, req in requirements.items():
        folder_path = DATASETS_DIR / req['folder']
        csv_files = list(folder_path.glob('*.csv'))
        
        if not csv_files:
            results[model_name] = {
                'ready': False,
                'reason': f"No hay archivos CSV en {req['folder']}/"
            }
            continue
        
        # Analizar primer archivo encontrado
        df = pd.read_csv(csv_files[0])
        
        if len(df) < req['min_rows']:
            results[model_name] = {
                'ready': False,
                'reason': f"Necesita mínimo {req['min_rows']} filas, tiene {len(df)}"
            }
            continue
        
        # Verificar columnas (flexible)
        has_required = any(
            col.lower() in [c.lower() for c in df.columns]
            for col in req['required_columns']
        )
        
        if not has_required:
            results[model_name] = {
                'ready': False,
                'reason': f"Falta alguna columna de: {', '.join(req['required_columns'])}"
            }
            continue
        
        results[model_name] = {
            'ready': True,
            'file': csv_files[0].name,
            'rows': len(df)
        }
    
    return results


def print_report():
    """Imprime reporte completo de datasets"""
    print("=" * 80)
    print("📊 ANÁLISIS DE DATASETS PARA MACHINE LEARNING")
    print("=" * 80)
    print()
    
    folders = ['clientes', 'productos', 'ventas', 'transacciones', 'inventario', 'raw']
    
    total_files = 0
    total_rows = 0
    
    for folder in folders:
        print(f"\n📁 {folder.upper()}/")
        print("-" * 80)
        
        results = scan_datasets_folder(folder)
        
        if not results:
            print("   ⚠️  No hay archivos CSV en esta carpeta")
            continue
        
        for stats in results:
            if 'error' in stats:
                print(f"   ❌ {stats['filename']}: ERROR - {stats['error']}")
                continue
            
            total_files += 1
            total_rows += stats['rows']
            
            print(f"\n   ✅ {stats['filename']}")
            print(f"      • Filas: {stats['rows']:,}")
            print(f"      • Columnas: {stats['columns']} - {', '.join(stats['column_names'][:5])}")
            
            if stats['duplicates'] > 0:
                print(f"      ⚠️  Duplicados: {stats['duplicates']}")
            
            missing = {k: v for k, v in stats['missing_values'].items() if v > 0}
            if missing:
                print(f"      ⚠️  Valores faltantes: {missing}")
            
            if stats['id_columns']:
                print(f"      • IDs encontrados: {', '.join(stats['id_columns'])}")
            
            if stats['date_columns']:
                print(f"      • Fechas encontradas: {', '.join(stats['date_columns'])}")
    
    print("\n" + "=" * 80)
    print(f"📈 RESUMEN TOTAL")
    print("=" * 80)
    print(f"   • Total archivos CSV: {total_files}")
    print(f"   • Total registros: {total_rows:,}")
    print()
    
    # Verificar requisitos para modelos
    print("=" * 80)
    print("🤖 DISPONIBILIDAD DE MODELOS ML")
    print("=" * 80)
    
    requirements = check_dataset_requirements()
    
    for model_name, status in requirements.items():
        if status['ready']:
            print(f"   ✅ {model_name}")
            print(f"      • Archivo: {status['file']}")
            print(f"      • Registros: {status['rows']:,}")
        else:
            print(f"   ❌ {model_name}")
            print(f"      • Razón: {status['reason']}")
        print()
    
    print("=" * 80)
    print(f"📝 Reporte generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Sugerencias
    models_ready = sum(1 for s in requirements.values() if s['ready'])
    if models_ready == 0:
        print("💡 SUGERENCIA: Sube tus datasets a las carpetas correspondientes.")
        print("   Ver: datasets/README.md para más información.")
    elif models_ready < len(requirements):
        print("💡 SUGERENCIA: Algunos modelos no tienen datos suficientes.")
        print("   Revisa los requisitos arriba y complementa los datasets faltantes.")
    else:
        print("🎉 ¡EXCELENTE! Todos los modelos tienen datos suficientes.")
        print("   Puedes proceder a entrenar los modelos con:")
        print("   python scripts/train_all_models.py")
    print()


if __name__ == '__main__':
    if not DATASETS_DIR.exists():
        print("❌ Error: Carpeta datasets/ no encontrada")
        print(f"   Esperado en: {DATASETS_DIR}")
        sys.exit(1)
    
    print_report()

