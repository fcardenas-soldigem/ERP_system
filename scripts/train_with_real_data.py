#!/usr/bin/env python3
"""
Script para entrenar modelos ML con los datasets reales
- retail_sales_dataset.csv → RFM + Churn
- Groceries_dataset.csv → Recomendaciones
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Agregar el backend al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.ml_models.customer_analytics.rfm_segmentation import RFMSegmentation
from apps.ml_models.customer_analytics.churn_prediction import ChurnPredictor
from apps.ml_models.product_recommendations.association_rules import ProductRecommender

DATASETS_DIR = Path(__file__).parent.parent / 'datasets'


def prepare_retail_sales_for_rfm():
    """
    Prepara retail_sales_dataset.csv para análisis RFM
    """
    print("\n" + "="*80)
    print("📊 PASO 1: Preparando datos de retail_sales para RFM...")
    print("="*80)
    
    df = pd.read_csv(DATASETS_DIR / 'productos' / 'retail_sales_dataset.csv')
    
    # Convertir fecha
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Calcular fecha de referencia (última fecha en el dataset)
    reference_date = df['Date'].max()
    print(f"📅 Fecha de referencia: {reference_date}")
    
    # Agrupar por cliente para calcular RFM
    rfm_data = df.groupby('Customer ID').agg({
        'Date': lambda x: (reference_date - x.max()).days,  # Recency
        'Transaction ID': 'count',  # Frequency
        'Total Amount': 'sum'  # Monetary
    }).reset_index()
    
    rfm_data.columns = ['cliente_id', 'recency', 'frequency', 'monetary']
    
    # Agregar información adicional
    customer_info = df.groupby('Customer ID').agg({
        'Date': ['min', 'max'],
        'Total Amount': 'mean',
        'Age': 'first',
        'Gender': 'first'
    }).reset_index()
    
    customer_info.columns = ['cliente_id', 'primera_compra', 'ultima_compra', 'avg_ticket', 'age', 'gender']
    customer_info['customer_age_days'] = (reference_date - customer_info['primera_compra']).dt.days
    
    # Combinar
    rfm_final = rfm_data.merge(customer_info[['cliente_id', 'customer_age_days', 'avg_ticket', 'age', 'gender']], 
                                on='cliente_id')
    
    print(f"✅ Datos preparados: {len(rfm_final)} clientes")
    print(f"   • Recency promedio: {rfm_final['recency'].mean():.1f} días")
    print(f"   • Frecuencia promedio: {rfm_final['frequency'].mean():.1f} compras")
    print(f"   • Valor promedio: ${rfm_final['monetary'].mean():.2f}")
    
    return rfm_final, df


def train_rfm_segmentation(rfm_data):
    """
    Entrena modelo de segmentación RFM
    """
    print("\n" + "="*80)
    print("🎯 PASO 2: Entrenando Segmentación RFM...")
    print("="*80)
    
    # Crear modelo
    rfm_model = RFMSegmentation(n_clusters=5)
    
    # Entrenar
    df_segmented = rfm_model.fit(rfm_data)
    
    # Estadísticas
    stats = rfm_model.get_segment_statistics(df_segmented)
    
    print("\n📊 Segmentos encontrados:")
    for segment_name, segment_stats in stats.items():
        print(f"\n   {segment_name}:")
        print(f"      • Clientes: {segment_stats['count']}")
        print(f"      • Recency: {segment_stats['avg_recency']:.0f} días")
        print(f"      • Frecuencia: {segment_stats['avg_frequency']:.1f} compras")
        print(f"      • Valor promedio: ${segment_stats['avg_monetary']:.2f}")
        print(f"      • Valor total: ${segment_stats['total_monetary']:.2f}")
    
    # Guardar modelo
    rfm_model.save_model()
    print("\n✅ Modelo RFM guardado exitosamente")
    
    # Guardar resultados
    output_file = DATASETS_DIR / 'processed' / 'rfm_segmentation_results.csv'
    df_segmented.to_csv(output_file, index=False)
    print(f"📄 Resultados guardados en: {output_file}")
    
    return df_segmented, stats


def train_churn_prediction(rfm_data):
    """
    Entrena modelo de predicción de churn
    """
    print("\n" + "="*80)
    print("⚠️  PASO 3: Entrenando Predicción de Churn...")
    print("="*80)
    
    # Crear modelo
    churn_model = ChurnPredictor()
    
    # Entrenar
    df_trained = churn_model.fit(rfm_data)
    
    # Predecir
    df_predicted = churn_model.predict(rfm_data)
    
    # Clientes en riesgo
    high_risk = df_predicted[df_predicted['churn_risk'] == 'Alto']
    medium_risk = df_predicted[df_predicted['churn_risk'] == 'Medio']
    
    print(f"\n📊 Resultados de Predicción:")
    print(f"   • Total clientes: {len(df_predicted)}")
    print(f"   • Riesgo ALTO: {len(high_risk)} clientes ({len(high_risk)/len(df_predicted)*100:.1f}%)")
    print(f"   • Riesgo MEDIO: {len(medium_risk)} clientes ({len(medium_risk)/len(df_predicted)*100:.1f}%)")
    print(f"   • Riesgo BAJO: {len(df_predicted[df_predicted['churn_risk'] == 'Bajo'])} clientes")
    
    if len(high_risk) > 0:
        print(f"\n🚨 Top 5 clientes en RIESGO CRÍTICO:")
        top_risk = df_predicted.nlargest(5, 'churn_probability')[['cliente_id', 'churn_probability', 'recency', 'frequency', 'monetary']]
        for idx, row in top_risk.iterrows():
            print(f"   • Cliente {row['cliente_id']}: {row['churn_probability']*100:.1f}% prob. churn")
            print(f"      - Último compra hace {row['recency']:.0f} días")
            print(f"      - {row['frequency']:.0f} compras, ${row['monetary']:.2f} total")
    
    # Feature importance
    importance = churn_model.get_feature_importance()
    print(f"\n📈 Factores más importantes para predecir churn:")
    for i, (feature, score) in enumerate(list(importance.items())[:5], 1):
        print(f"   {i}. {feature}: {score:.3f}")
    
    # Guardar modelo
    churn_model.save_model()
    print("\n✅ Modelo de Churn guardado exitosamente")
    
    # Guardar resultados
    output_file = DATASETS_DIR / 'processed' / 'churn_prediction_results.csv'
    df_predicted.to_csv(output_file, index=False)
    print(f"📄 Resultados guardados en: {output_file}")
    
    return df_predicted


def demographic_analysis(retail_df):
    """
    Análisis demográfico (edad, género)
    """
    print("\n" + "="*80)
    print("👥 PASO 4: Análisis Demográfico...")
    print("="*80)
    
    # Por género
    gender_stats = retail_df.groupby('Gender').agg({
        'Total Amount': ['sum', 'mean', 'count'],
        'Quantity': 'sum'
    }).round(2)
    
    print("\n📊 Análisis por Género:")
    print(gender_stats)
    
    # Por edad
    retail_df['Age Group'] = pd.cut(retail_df['Age'], 
                                     bins=[0, 25, 35, 45, 55, 100],
                                     labels=['18-25', '26-35', '36-45', '46-55', '55+'])
    
    age_stats = retail_df.groupby('Age Group').agg({
        'Total Amount': ['sum', 'mean', 'count'],
        'Quantity': 'sum'
    }).round(2)
    
    print("\n📊 Análisis por Grupo de Edad:")
    print(age_stats)
    
    # Por categoría
    category_stats = retail_df.groupby('Product Category').agg({
        'Total Amount': ['sum', 'mean', 'count'],
        'Quantity': 'sum'
    }).round(2)
    
    print("\n📊 Análisis por Categoría de Producto:")
    print(category_stats)
    
    # Guardar análisis
    output_file = DATASETS_DIR / 'processed' / 'demographic_analysis.csv'
    combined_stats = pd.DataFrame({
        'Gender': gender_stats,
        'Age_Group': age_stats,
        'Category': category_stats
    })
    combined_stats.to_csv(output_file)
    print(f"\n✅ Análisis demográfico guardado en: {output_file}")


def prepare_groceries_for_recommendations():
    """
    Prepara Groceries_dataset.csv para recomendaciones
    """
    print("\n" + "="*80)
    print("🛒 PASO 5: Preparando Groceries para Recomendaciones...")
    print("="*80)
    
    df = pd.read_csv(DATASETS_DIR / 'inventario' / 'Groceries_dataset.csv')
    
    print(f"✅ Datos cargados: {len(df):,} items")
    print(f"   • {df['Member_number'].nunique():,} clientes")
    print(f"   • {df['itemDescription'].nunique()} productos únicos")
    
    # Crear IDs para transacciones (agrupar por cliente y fecha)
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
    df['transaction_id'] = df.groupby(['Member_number', 'Date']).ngroup()
    
    # Crear IDs numéricos para productos
    product_mapping = {prod: idx for idx, prod in enumerate(df['itemDescription'].unique())}
    df['producto_id'] = df['itemDescription'].map(product_mapping)
    
    # Preparar formato para modelo
    transactions_df = df[['transaction_id', 'producto_id', 'itemDescription']].copy()
    
    print(f"✅ Transacciones preparadas: {df['transaction_id'].nunique():,} transacciones")
    
    # Guardar mapeo de productos
    product_map_df = pd.DataFrame([
        {'producto_id': pid, 'nombre': name}
        for name, pid in product_mapping.items()
    ])
    product_map_file = DATASETS_DIR / 'processed' / 'product_mapping.csv'
    product_map_df.to_csv(product_map_file, index=False)
    print(f"📄 Mapeo de productos guardado en: {product_map_file}")
    
    return transactions_df, product_mapping


def train_product_recommendations(transactions_df, product_mapping):
    """
    Entrena modelo de recomendaciones de productos
    """
    print("\n" + "="*80)
    print("🎯 PASO 6: Entrenando Recomendaciones de Productos...")
    print("="*80)
    
    # Crear modelo
    recommender = ProductRecommender(
        min_support=0.01,
        min_confidence=0.2,
        min_lift=1.0
    )
    
    # Entrenar
    try:
        rules = recommender.fit(transactions_df)
        
        print(f"\n✅ Modelo entrenado exitosamente!")
        print(f"   • Reglas de asociación encontradas: {len(rules)}")
        
        # Estadísticas
        stats = recommender.get_statistics()
        print(f"\n📊 Estadísticas del Modelo:")
        print(f"   • Total reglas: {stats['total_rules']}")
        print(f"   • Itemsets frecuentes: {stats['total_frequent_itemsets']}")
        print(f"   • Confidence promedio: {stats['avg_confidence']:.1f}%")
        print(f"   • Lift promedio: {stats['avg_lift']:.2f}")
        print(f"   • Lift máximo: {stats['max_lift']:.2f}")
        
        # Top pares de productos
        top_pairs = recommender.get_top_product_pairs(top_n=10)
        
        print(f"\n🏆 Top 10 Combinaciones de Productos:")
        reverse_mapping = {v: k for k, v in product_mapping.items()}
        
        for i, pair in enumerate(top_pairs, 1):
            prod_a = reverse_mapping.get(pair['product_a_id'], 'Unknown')
            prod_b = reverse_mapping.get(pair['product_b_id'], 'Unknown')
            print(f"   {i}. '{prod_a}' → '{prod_b}'")
            print(f"      Confidence: {pair['confidence']:.1f}%, Lift: {pair['lift']:.2f}")
        
        # Guardar modelo
        recommender.save_model()
        print("\n✅ Modelo de Recomendaciones guardado exitosamente")
        
        # Guardar pares top
        top_pairs_df = pd.DataFrame(top_pairs)
        top_pairs_df['product_a_name'] = top_pairs_df['product_a_id'].map(reverse_mapping)
        top_pairs_df['product_b_name'] = top_pairs_df['product_b_id'].map(reverse_mapping)
        
        output_file = DATASETS_DIR / 'processed' / 'top_product_pairs.csv'
        top_pairs_df.to_csv(output_file, index=False)
        print(f"📄 Top pares guardados en: {output_file}")
        
        return recommender, top_pairs
        
    except Exception as e:
        print(f"❌ Error entrenando modelo: {e}")
        return None, []


def generate_final_report():
    """
    Genera reporte final con todos los resultados
    """
    print("\n" + "="*80)
    print("📋 PASO 7: Generando Reporte Final...")
    print("="*80)
    
    report = []
    report.append("="*80)
    report.append("🎉 ENTRENAMIENTO DE MODELOS ML COMPLETADO")
    report.append("="*80)
    report.append("")
    report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Verificar archivos generados
    processed_dir = DATASETS_DIR / 'processed'
    report.append("📁 Archivos Generados:")
    for file in processed_dir.glob('*.csv'):
        report.append(f"   ✅ {file.name}")
    
    report.append("")
    report.append("🤖 Modelos Entrenados:")
    
    # Verificar modelos guardados
    models_dir = Path(__file__).parent.parent / 'backend' / 'ml_models_cache'
    if models_dir.exists():
        for model_file in models_dir.glob('*.pkl'):
            report.append(f"   ✅ {model_file.name}")
    
    report.append("")
    report.append("🚀 Próximos Pasos:")
    report.append("   1. Revisar resultados en datasets/processed/")
    report.append("   2. Probar APIs:")
    report.append("      • POST /api/ml/customers/segment/")
    report.append("      • POST /api/ml/customers/churn/")
    report.append("      • POST /api/ml/products/recommendations/")
    report.append("   3. Integrar en el frontend")
    report.append("")
    report.append("="*80)
    
    report_text = "\n".join(report)
    print(report_text)
    
    # Guardar reporte
    report_file = DATASETS_DIR / 'processed' / f'training_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    with open(report_file, 'w') as f:
        f.write(report_text)
    
    print(f"\n✅ Reporte guardado en: {report_file}")


def main():
    """
    Función principal
    """
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "   🤖 ENTRENAMIENTO DE MODELOS ML CON DATOS REALES   ".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    try:
        # Crear carpeta processed si no existe
        processed_dir = DATASETS_DIR / 'processed'
        processed_dir.mkdir(exist_ok=True)
        
        # PARTE 1: Retail Sales (RFM + Churn + Demográfico)
        rfm_data, retail_df = prepare_retail_sales_for_rfm()
        df_segmented, rfm_stats = train_rfm_segmentation(rfm_data)
        df_churn = train_churn_prediction(rfm_data)
        demographic_analysis(retail_df)
        
        # PARTE 2: Groceries (Recomendaciones)
        transactions_df, product_mapping = prepare_groceries_for_recommendations()
        recommender, top_pairs = train_product_recommendations(transactions_df, product_mapping)
        
        # Reporte Final
        generate_final_report()
        
        print("\n" + "="*80)
        print("✅ ¡ENTRENAMIENTO COMPLETADO EXITOSAMENTE!")
        print("="*80)
        print("\n💡 Ahora puedes usar las APIs de ML con tus modelos entrenados.")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error durante el entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

