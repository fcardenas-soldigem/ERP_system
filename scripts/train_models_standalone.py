#!/usr/bin/env python3
"""
Script standalone para entrenar modelos ML con los datasets reales
No requiere Django - usa solo pandas, sklearn y mlxtend
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Importaciones ML
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
import joblib

DATASETS_DIR = Path(__file__).parent.parent / 'datasets'
MODELS_DIR = Path(__file__).parent.parent / 'backend' / 'ml_models_cache'
MODELS_DIR.mkdir(exist_ok=True)


def prepare_retail_sales_for_rfm():
    """Prepara retail_sales_dataset.csv para análisis RFM"""
    print("\n" + "="*80)
    print("📊 PASO 1: Preparando datos de retail_sales para RFM...")
    print("="*80)
    
    df = pd.read_csv(DATASETS_DIR / 'ventas' / 'retail_sales_dataset.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    reference_date = df['Date'].max()
    
    print(f"📅 Fecha de referencia: {reference_date}")
    
    # Calcular RFM
    rfm_data = df.groupby('Customer ID').agg({
        'Date': lambda x: (reference_date - x.max()).days,
        'Transaction ID': 'count',
        'Total Amount': 'sum'
    }).reset_index()
    
    rfm_data.columns = ['cliente_id', 'recency', 'frequency', 'monetary']
    
    # Info adicional
    customer_info = df.groupby('Customer ID').agg({
        'Date': ['min', 'max'],
        'Total Amount': 'mean',
        'Age': 'first',
        'Gender': 'first',
        'Product Category': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    }).reset_index()
    
    customer_info.columns = ['cliente_id', 'primera_compra', 'ultima_compra', 'avg_ticket', 'age', 'gender', 'fav_category']
    customer_info['customer_age_days'] = (reference_date - customer_info['primera_compra']).dt.days
    
    rfm_final = rfm_data.merge(customer_info[['cliente_id', 'customer_age_days', 'avg_ticket', 'age', 'gender', 'fav_category']], 
                                on='cliente_id')
    
    print(f"✅ Datos preparados: {len(rfm_final)} clientes")
    print(f"   • Recency promedio: {rfm_final['recency'].mean():.1f} días")
    print(f"   • Frecuencia promedio: {rfm_final['frequency'].mean():.1f} compras")
    print(f"   • Valor promedio: ${rfm_final['monetary'].mean():.2f}")
    
    return rfm_final, df


def train_rfm_segmentation(rfm_data):
    """Entrena modelo de segmentación RFM"""
    print("\n" + "="*80)
    print("🎯 PASO 2: Entrenando Segmentación RFM...")
    print("="*80)
    
    # Preparar datos
    features = ['recency', 'frequency', 'monetary']
    X = rfm_data[features].copy()
    
    # Normalizar
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # KMeans
    n_clusters = 5
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    rfm_data['cluster'] = kmeans.fit_predict(X_scaled)
    
    # Asignar nombres a segmentos
    segment_names = {
        0: 'Champions',
        1: 'Loyal Customers', 
        2: 'At Risk',
        3: 'Lost',
        4: 'Potential'
    }
    
    # Analizar clusters para asignar nombres correctamente
    cluster_stats = rfm_data.groupby('cluster')[features].mean()
    
    # Ordenar por valor (monetary)
    sorted_clusters = cluster_stats.sort_values('monetary', ascending=False).index.tolist()
    
    # Reasignar nombres
    segment_mapping = {}
    names = ['Champions', 'Loyal Customers', 'Potential', 'At Risk', 'Lost']
    for i, cluster_id in enumerate(sorted_clusters):
        segment_mapping[cluster_id] = names[i]
    
    rfm_data['segment'] = rfm_data['cluster'].map(segment_mapping)
    
    # Estadísticas por segmento
    print("\n📊 Segmentos encontrados:")
    for segment in names:
        segment_data = rfm_data[rfm_data['segment'] == segment]
        if len(segment_data) > 0:
            print(f"\n   {segment}:")
            print(f"      • Clientes: {len(segment_data)}")
            print(f"      • Recency: {segment_data['recency'].mean():.0f} días")
            print(f"      • Frecuencia: {segment_data['frequency'].mean():.1f} compras")
            print(f"      • Valor promedio: ${segment_data['monetary'].mean():.2f}")
            print(f"      • Valor total: ${segment_data['monetary'].sum():.2f}")
    
    # Guardar modelo
    model_data = {
        'kmeans': kmeans,
        'scaler': scaler,
        'segment_mapping': segment_mapping,
        'features': features
    }
    joblib.dump(model_data, MODELS_DIR / 'rfm_segmentation_model.pkl')
    print("\n✅ Modelo RFM guardado en ml_models_cache/rfm_segmentation_model.pkl")
    
    # Guardar resultados
    output_file = DATASETS_DIR / 'processed' / 'rfm_segmentation_results.csv'
    rfm_data.to_csv(output_file, index=False)
    print(f"📄 Resultados guardados en: {output_file}")
    
    return rfm_data


def train_churn_prediction(rfm_data):
    """Entrena modelo de predicción de churn"""
    print("\n" + "="*80)
    print("⚠️  PASO 3: Entrenando Predicción de Churn...")
    print("="*80)
    
    # Definir churn: clientes con recency > 90 días
    churn_threshold = 90
    rfm_data['is_churned'] = (rfm_data['recency'] > churn_threshold).astype(int)
    
    print(f"📊 Definición de churn: clientes sin compras en {churn_threshold}+ días")
    print(f"   • Churned: {rfm_data['is_churned'].sum()} ({rfm_data['is_churned'].mean()*100:.1f}%)")
    print(f"   • Activos: {(1-rfm_data['is_churned']).sum()} ({(1-rfm_data['is_churned'].mean())*100:.1f}%)")
    
    # Features para el modelo
    feature_cols = ['recency', 'frequency', 'monetary', 'customer_age_days', 'avg_ticket', 'age']
    X = rfm_data[feature_cols].copy()
    y = rfm_data['is_churned']
    
    # Entrenar modelo
    clf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
    clf.fit(X, y)
    
    # Predecir probabilidades
    rfm_data['churn_probability'] = clf.predict_proba(X)[:, 1]
    
    # Clasificar riesgo
    rfm_data['churn_risk'] = pd.cut(
        rfm_data['churn_probability'],
        bins=[0, 0.3, 0.7, 1.0],
        labels=['Bajo', 'Medio', 'Alto']
    )
    
    # Estadísticas
    high_risk = rfm_data[rfm_data['churn_risk'] == 'Alto']
    medium_risk = rfm_data[rfm_data['churn_risk'] == 'Medio']
    low_risk = rfm_data[rfm_data['churn_risk'] == 'Bajo']
    
    print(f"\n📊 Resultados de Predicción:")
    print(f"   • Total clientes: {len(rfm_data)}")
    print(f"   • Riesgo ALTO: {len(high_risk)} clientes ({len(high_risk)/len(rfm_data)*100:.1f}%)")
    print(f"   • Riesgo MEDIO: {len(medium_risk)} clientes ({len(medium_risk)/len(rfm_data)*100:.1f}%)")
    print(f"   • Riesgo BAJO: {len(low_risk)} clientes ({len(low_risk)/len(rfm_data)*100:.1f}%)")
    
    if len(high_risk) > 0:
        print(f"\n🚨 Top 5 clientes en RIESGO CRÍTICO:")
        top_risk = rfm_data.nlargest(5, 'churn_probability')[['cliente_id', 'churn_probability', 'recency', 'frequency', 'monetary']]
        for idx, row in top_risk.iterrows():
            print(f"   • Cliente {row['cliente_id']}: {row['churn_probability']*100:.1f}% prob. churn")
            print(f"      - Última compra hace {row['recency']:.0f} días")
            print(f"      - {row['frequency']:.0f} compras, ${row['monetary']:.2f} total")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': clf.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\n📈 Factores más importantes para predecir churn:")
    for idx, row in feature_importance.iterrows():
        print(f"   • {row['feature']}: {row['importance']:.3f}")
    
    # Guardar modelo
    model_data = {
        'model': clf,
        'features': feature_cols,
        'churn_threshold': churn_threshold
    }
    joblib.dump(model_data, MODELS_DIR / 'churn_prediction_model.pkl')
    print("\n✅ Modelo de Churn guardado en ml_models_cache/churn_prediction_model.pkl")
    
    # Guardar resultados
    output_file = DATASETS_DIR / 'processed' / 'churn_prediction_results.csv'
    rfm_data.to_csv(output_file, index=False)
    print(f"📄 Resultados guardados en: {output_file}")
    
    return rfm_data


def demographic_analysis(retail_df):
    """Análisis demográfico"""
    print("\n" + "="*80)
    print("👥 PASO 4: Análisis Demográfico...")
    print("="*80)
    
    # Por género
    print("\n📊 Ventas por Género:")
    gender_stats = retail_df.groupby('Gender').agg({
        'Total Amount': ['sum', 'mean', 'count'],
        'Quantity': 'sum'
    }).round(2)
    print(gender_stats)
    
    # Por edad
    retail_df['Age Group'] = pd.cut(retail_df['Age'], 
                                     bins=[0, 25, 35, 45, 55, 100],
                                     labels=['18-25', '26-35', '36-45', '46-55', '55+'])
    
    print("\n📊 Ventas por Grupo de Edad:")
    age_stats = retail_df.groupby('Age Group').agg({
        'Total Amount': ['sum', 'mean', 'count'],
        'Quantity': 'sum'
    }).round(2)
    print(age_stats)
    
    # Por categoría
    print("\n📊 Ventas por Categoría:")
    category_stats = retail_df.groupby('Product Category').agg({
        'Total Amount': ['sum', 'mean', 'count'],
        'Quantity': 'sum'
    }).round(2)
    print(category_stats)
    
    # Guardar
    output_file = DATASETS_DIR / 'processed' / 'demographic_analysis.txt'
    with open(output_file, 'w') as f:
        f.write("ANÁLISIS DEMOGRÁFICO\n")
        f.write("="*80 + "\n\n")
        f.write("POR GÉNERO:\n")
        f.write(str(gender_stats) + "\n\n")
        f.write("POR EDAD:\n")
        f.write(str(age_stats) + "\n\n")
        f.write("POR CATEGORÍA:\n")
        f.write(str(category_stats) + "\n")
    
    print(f"\n✅ Análisis guardado en: {output_file}")


def prepare_groceries_for_recommendations():
    """Prepara Groceries para recomendaciones"""
    print("\n" + "="*80)
    print("🛒 PASO 5: Preparando Groceries para Recomendaciones...")
    print("="*80)
    
    df = pd.read_csv(DATASETS_DIR / 'inventario' / 'Groceries_dataset.csv')
    
    print(f"✅ Datos cargados: {len(df):,} items")
    print(f"   • {df['Member_number'].nunique():,} clientes")
    print(f"   • {df['itemDescription'].nunique()} productos únicos")
    
    # Crear transaction IDs
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
    df['transaction_id'] = df.groupby(['Member_number', 'Date']).ngroup()
    
    print(f"✅ Transacciones preparadas: {df['transaction_id'].nunique():,} transacciones")
    
    return df


def train_product_recommendations(transactions_df):
    """Entrena modelo de recomendaciones"""
    print("\n" + "="*80)
    print("🎯 PASO 6: Entrenando Recomendaciones de Productos...")
    print("="*80)
    
    # Crear matriz transaccional
    print("Creando matriz transaccional...")
    basket = transactions_df.groupby(['transaction_id', 'itemDescription'])['itemDescription'].count().unstack().reset_index().fillna(0).set_index('transaction_id')
    
    # Convertir a binario
    basket_binary = basket.applymap(lambda x: 1 if x > 0 else 0)
    
    print(f"   • Matriz: {basket_binary.shape[0]} transacciones × {basket_binary.shape[1]} productos")
    
    # Calcular soporte mínimo dinámico
    n_transactions = len(basket_binary)
    min_support = max(0.005, 10 / n_transactions)  # Mínimo 10 transacciones o 0.5%
    
    print(f"   • Soporte mínimo: {min_support:.4f} ({int(min_support * n_transactions)} transacciones)")
    
    # Encontrar itemsets frecuentes
    print("Buscando itemsets frecuentes...")
    frequent_itemsets = apriori(basket_binary, min_support=min_support, use_colnames=True, max_len=2)
    
    if len(frequent_itemsets) == 0:
        print("❌ No se encontraron itemsets frecuentes. Ajustando parámetros...")
        min_support = 5 / n_transactions
        frequent_itemsets = apriori(basket_binary, min_support=min_support, use_colnames=True, max_len=2)
    
    print(f"   • Itemsets frecuentes encontrados: {len(frequent_itemsets)}")
    
    # Generar reglas
    print("Generando reglas de asociación...")
    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.1)
    
    if len(rules) == 0:
        print("⚠️  No se generaron reglas con los parámetros actuales")
        return None
    
    # Calcular lift
    rules = rules[rules['lift'] > 1.0]
    rules = rules.sort_values('lift', ascending=False)
    
    print(f"\n✅ Modelo entrenado exitosamente!")
    print(f"   • Reglas de asociación: {len(rules)}")
    print(f"   • Confidence promedio: {rules['confidence'].mean()*100:.1f}%")
    print(f"   • Lift promedio: {rules['lift'].mean():.2f}")
    print(f"   • Lift máximo: {rules['lift'].max():.2f}")
    
    # Top recomendaciones
    print(f"\n🏆 Top 10 Combinaciones de Productos:")
    for i, (idx, row) in enumerate(rules.head(10).iterrows(), 1):
        antecedent = ', '.join(list(row['antecedents']))
        consequent = ', '.join(list(row['consequents']))
        print(f"   {i}. '{antecedent}' → '{consequent}'")
        print(f"      Confidence: {row['confidence']*100:.1f}%, Lift: {row['lift']:.2f}, Support: {row['support']*100:.2f}%")
    
    # Guardar modelo
    model_data = {
        'rules': rules,
        'frequent_itemsets': frequent_itemsets,
        'products': list(basket_binary.columns),
        'min_support': min_support
    }
    joblib.dump(model_data, MODELS_DIR / 'product_recommendations_model.pkl')
    print("\n✅ Modelo guardado en ml_models_cache/product_recommendations_model.pkl")
    
    # Guardar top reglas
    output_file = DATASETS_DIR / 'processed' / 'top_product_recommendations.csv'
    rules_to_save = rules.head(50).copy()
    rules_to_save['antecedents'] = rules_to_save['antecedents'].apply(lambda x: ', '.join(list(x)))
    rules_to_save['consequents'] = rules_to_save['consequents'].apply(lambda x: ', '.join(list(x)))
    rules_to_save.to_csv(output_file, index=False)
    print(f"📄 Top reglas guardadas en: {output_file}")
    
    return rules


def generate_final_report():
    """Genera reporte final"""
    print("\n" + "="*80)
    print("📋 GENERANDO REPORTE FINAL...")
    print("="*80)
    
    report = []
    report.append("="*80)
    report.append("🎉 ENTRENAMIENTO DE MODELOS ML COMPLETADO")
    report.append("="*80)
    report.append("")
    report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    report.append("📁 Archivos Generados:")
    processed_dir = DATASETS_DIR / 'processed'
    for file in sorted(processed_dir.glob('*')):
        report.append(f"   ✅ {file.name}")
    
    report.append("")
    report.append("🤖 Modelos Entrenados:")
    for model_file in sorted(MODELS_DIR.glob('*.pkl')):
        report.append(f"   ✅ {model_file.name}")
    
    report.append("")
    report.append("🚀 Próximos Pasos:")
    report.append("   1. Revisar resultados en datasets/processed/")
    report.append("   2. Integrar modelos en las APIs de Django")
    report.append("   3. Crear visualizaciones en el frontend")
    report.append("   4. Configurar reentrenamiento periódico")
    report.append("")
    report.append("="*80)
    
    report_text = "\n".join(report)
    print(report_text)
    
    report_file = DATASETS_DIR / 'processed' / f'training_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    with open(report_file, 'w') as f:
        f.write(report_text)
    
    print(f"\n✅ Reporte guardado en: {report_file}")


def main():
    """Función principal"""
    print("\n")
    print("█" * 80)
    print("█" + "  🤖 ENTRENAMIENTO DE MODELOS ML CON DATOS REALES  ".center(78) + "█")
    print("█" * 80)
    
    try:
        # Crear carpeta processed
        processed_dir = DATASETS_DIR / 'processed'
        processed_dir.mkdir(exist_ok=True)
        
        # PARTE 1: Retail Sales
        rfm_data, retail_df = prepare_retail_sales_for_rfm()
        rfm_data = train_rfm_segmentation(rfm_data)
        rfm_data = train_churn_prediction(rfm_data)
        demographic_analysis(retail_df)
        
        # PARTE 2: Groceries
        groceries_df = prepare_groceries_for_recommendations()
        rules = train_product_recommendations(groceries_df)
        
        # Reporte Final
        generate_final_report()
        
        print("\n" + "="*80)
        print("✅ ¡ENTRENAMIENTO COMPLETADO EXITOSAMENTE!")
        print("="*80)
        print("\n💡 Los modelos están listos para ser usados en las APIs.")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error durante el entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

