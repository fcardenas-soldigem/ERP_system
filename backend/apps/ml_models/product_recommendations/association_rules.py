"""
Recomendación de Productos usando Association Rules (Market Basket Analysis)
Encuentra productos que se compran frecuentemente juntos
"""
import pandas as pd
import numpy as np
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
import joblib
import os
from django.conf import settings


class ProductRecommender:
    """
    Sistema de recomendación basado en reglas de asociación
    """
    
    def __init__(self, min_support=0.01, min_confidence=0.3, min_lift=1.0, model_path=None):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.rules = None
        self.frequent_itemsets = None
        if model_path:
            self.model_path = model_path
        else:
            self.model_path = os.path.join(settings.BASE_DIR, 'ml_models_cache', 'product_recommendations.pkl')
    
    def fit(self, df_transactions):
        """
        Entrena el modelo de recomendación
        
        Args:
            df_transactions: DataFrame con columnas transaction_id, producto_id
        """
        if df_transactions.empty:
            raise ValueError("No hay transacciones para analizar")
        
        # Crear matriz de transacciones (basket)
        basket = df_transactions.groupby(['transaction_id', 'producto_id'])['producto_id'].count().unstack().fillna(0)
        basket = basket.applymap(lambda x: 1 if x > 0 else 0)
        
        # Encontrar itemsets frecuentes
        self.frequent_itemsets = apriori(basket, min_support=self.min_support, use_colnames=True)
        
        if self.frequent_itemsets.empty:
            raise ValueError("No se encontraron patrones frecuentes. Intenta reducir min_support")
        
        # Generar reglas de asociación
        self.rules = association_rules(
            self.frequent_itemsets,
            metric="confidence",
            min_threshold=self.min_confidence
        )
        
        # Filtrar por lift
        self.rules = self.rules[self.rules['lift'] >= self.min_lift]
        
        # Ordenar por lift
        self.rules = self.rules.sort_values('lift', ascending=False)
        
        return self.rules
    
    def recommend_for_product(self, producto_id, top_n=5):
        """
        Recomienda productos basados en un producto dado
        
        Args:
            producto_id: ID del producto
            top_n: Número de recomendaciones a retornar
        
        Returns:
            Lista de productos recomendados con métricas
        """
        if self.rules is None or self.rules.empty:
            return []
        
        # Filtrar reglas donde el producto está en antecedents
        product_rules = self.rules[
            self.rules['antecedents'].apply(lambda x: producto_id in x)
        ].copy()
        
        if product_rules.empty:
            return []
        
        # Extraer productos consecuentes
        recommendations = []
        for _, rule in product_rules.head(top_n).iterrows():
            for consequent_id in rule['consequents']:
                if consequent_id != producto_id:
                    recommendations.append({
                        'producto_id': consequent_id,
                        'confidence': round(rule['confidence'] * 100, 2),
                        'lift': round(rule['lift'], 2),
                        'support': round(rule['support'] * 100, 2)
                    })
        
        return recommendations[:top_n]
    
    def recommend_for_basket(self, producto_ids, top_n=5):
        """
        Recomienda productos basados en una canasta de productos
        
        Args:
            producto_ids: Lista de IDs de productos en la canasta
            top_n: Número de recomendaciones a retornar
        """
        if self.rules is None or self.rules.empty:
            return []
        
        producto_ids_set = set(producto_ids)
        
        # Filtrar reglas donde todos los productos están en antecedents
        basket_rules = self.rules[
            self.rules['antecedents'].apply(lambda x: x.issubset(producto_ids_set))
        ].copy()
        
        if basket_rules.empty:
            # Si no hay reglas exactas, buscar reglas con al menos un producto
            basket_rules = self.rules[
                self.rules['antecedents'].apply(lambda x: len(x.intersection(producto_ids_set)) > 0)
            ].copy()
        
        if basket_rules.empty:
            return []
        
        # Extraer recomendaciones
        recommendations = []
        seen_products = set(producto_ids)
        
        for _, rule in basket_rules.iterrows():
            for consequent_id in rule['consequents']:
                if consequent_id not in seen_products:
                    recommendations.append({
                        'producto_id': consequent_id,
                        'confidence': round(rule['confidence'] * 100, 2),
                        'lift': round(rule['lift'], 2),
                        'support': round(rule['support'] * 100, 2),
                        'matched_products': len(rule['antecedents'].intersection(producto_ids_set))
                    })
                    seen_products.add(consequent_id)
        
        # Ordenar por lift y confidence
        recommendations.sort(key=lambda x: (x['lift'], x['confidence']), reverse=True)
        
        return recommendations[:top_n]
    
    def get_top_product_pairs(self, top_n=10):
        """
        Retorna los pares de productos más frecuentemente comprados juntos
        """
        if self.rules is None or self.rules.empty:
            return []
        
        # Filtrar reglas con solo 1 producto en cada lado
        pairs = self.rules[
            (self.rules['antecedents'].apply(len) == 1) &
            (self.rules['consequents'].apply(len) == 1)
        ].copy()
        
        if pairs.empty:
            return []
        
        # Extraer pares
        pairs_list = []
        for _, rule in pairs.head(top_n).iterrows():
            product_a = list(rule['antecedents'])[0]
            product_b = list(rule['consequents'])[0]
            
            pairs_list.append({
                'product_a_id': product_a,
                'product_b_id': product_b,
                'confidence': round(rule['confidence'] * 100, 2),
                'lift': round(rule['lift'], 2),
                'support': round(rule['support'] * 100, 2)
            })
        
        return pairs_list
    
    def get_statistics(self):
        """
        Retorna estadísticas del modelo
        """
        if self.rules is None:
            return {}
        
        return {
            'total_rules': len(self.rules),
            'total_frequent_itemsets': len(self.frequent_itemsets) if self.frequent_itemsets is not None else 0,
            'avg_confidence': round(self.rules['confidence'].mean() * 100, 2),
            'avg_lift': round(self.rules['lift'].mean(), 2),
            'max_lift': round(self.rules['lift'].max(), 2),
            'min_support_used': self.min_support,
            'min_confidence_used': self.min_confidence
        }
    
    def save_model(self):
        """Guarda el modelo entrenado"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            'rules': self.rules,
            'frequent_itemsets': self.frequent_itemsets,
            'min_support': self.min_support,
            'min_confidence': self.min_confidence,
            'min_lift': self.min_lift
        }, self.model_path)
    
    def load_model(self):
        """Carga el modelo guardado"""
        if os.path.exists(self.model_path):
            data = joblib.load(self.model_path)
            self.rules = data['rules']
            self.frequent_itemsets = data['frequent_itemsets']
            self.min_support = data['min_support']
            self.min_confidence = data['min_confidence']
            self.min_lift = data['min_lift']
            return True
        return False


def train_recommendation_model(empresa_id=None):
    """
    Entrena el modelo de recomendación de productos
    
    Returns:
        dict con resultados del entrenamiento
    """
    from apps.ml_models.utils.data_preparation import prepare_product_transactions
    
    # Preparar datos
    df = prepare_product_transactions(empresa_id)
    
    if df.empty or len(df) < 10:
        return {
            'success': False,
            'message': 'No hay suficientes transacciones para entrenar el modelo',
            'statistics': {}
        }
    
    # Crear y entrenar modelo
    recommender = ProductRecommender(
        min_support=0.01,
        min_confidence=0.2,
        min_lift=1.0
    )
    
    try:
        recommender.fit(df)
        
        # Obtener estadísticas
        stats = recommender.get_statistics()
        
        # Obtener top pares de productos
        top_pairs = recommender.get_top_product_pairs(top_n=20)
        
        # Guardar modelo
        recommender.save_model()
        
        return {
            'success': True,
            'statistics': stats,
            'top_product_pairs': top_pairs,
            'message': f'Modelo entrenado exitosamente con {stats["total_rules"]} reglas'
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error al entrenar modelo: {str(e)}',
            'statistics': {}
        }


def get_product_recommendations(producto_id=None, producto_ids=None, top_n=5, empresa_id=None):
    """
    Obtiene recomendaciones de productos
    
    Args:
        producto_id: ID de un solo producto
        producto_ids: Lista de IDs de productos (canasta)
        top_n: Número de recomendaciones
        empresa_id: ID de la empresa
    
    Returns:
        dict con recomendaciones
    """
    from apps.ml_models.utils.data_preparation import get_product_info
    
    # Cargar modelo
    recommender = ProductRecommender()
    
    if not recommender.load_model():
        # Si no existe modelo, entrenar uno nuevo
        train_result = train_recommendation_model(empresa_id)
        if not train_result['success']:
            return {
                'success': False,
                'message': 'No se pudo entrenar el modelo de recomendación',
                'recommendations': []
            }
        recommender.load_model()
    
    try:
        # Obtener recomendaciones
        if producto_id:
            recommendations = recommender.recommend_for_product(producto_id, top_n)
        elif producto_ids:
            recommendations = recommender.recommend_for_basket(producto_ids, top_n)
        else:
            return {
                'success': False,
                'message': 'Debe proporcionar producto_id o producto_ids',
                'recommendations': []
            }
        
        # Enriquecer con información del producto
        enriched_recommendations = []
        for rec in recommendations:
            product_info = get_product_info(rec['producto_id'])
            if product_info:
                enriched_recommendations.append({
                    **product_info,
                    'confidence': rec['confidence'],
                    'lift': rec['lift'],
                    'support': rec['support'],
                    'recommendation_strength': 'Alta' if rec['lift'] > 2 else 'Media' if rec['lift'] > 1.5 else 'Normal'
                })
        
        return {
            'success': True,
            'recommendations': enriched_recommendations,
            'count': len(enriched_recommendations),
            'message': f'Se encontraron {len(enriched_recommendations)} recomendaciones'
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error al obtener recomendaciones: {str(e)}',
            'recommendations': []
        }

