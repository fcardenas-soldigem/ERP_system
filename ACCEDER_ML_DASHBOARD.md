# 🎯 Cómo Acceder al ML Dashboard

## ✅ Ruta Agregada Exitosamente

La ruta del ML Dashboard ya está configurada en tu sistema.

---

## 🚀 Cómo Acceder:

### Opción 1: URL Directa
```
http://localhost:3000/ml-dashboard
```

### Opción 2: Agregar al Menú (Recomendado)

Busca el componente de tu Sidebar/Menu y agrega:

```jsx
import { SmartToy } from '@mui/icons-material';

// Dentro de tu lista de menú:
<ListItem button onClick={() => navigate('/ml-dashboard')}>
  <ListItemIcon>
    <SmartToy />
  </ListItemIcon>
  <ListItemText primary="Machine Learning" />
</ListItem>
```

---

## 📊 Lo que Verás en el Dashboard:

### Al cargar por primera vez:

```
┌─────────────────────────────────────────────────┐
│  🤖 Machine Learning Dashboard                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  📊 Datos Disponibles:                          │
│  • X ventas registradas                         │
│  • Y clientes                                   │
│  • Z productos                                  │
│                                                 │
│  ⚠️ Modelos sin entrenar                        │
│  [Entrenar Modelos] ← Botón para iniciar       │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Después de entrenar:

```
┌─────────────────────────────────────────────────┐
│  🤖 Machine Learning Dashboard                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ✅ Segmentación RFM: v1 - Activo               │
│  ✅ Predicción Churn: v1 - Activo               │
│  ✅ Recomendaciones: v1 - Activo                │
│                                                 │
│  Tabs:                                          │
│  [👥 Segmentación] [⚠️ Churn] [🛒 Productos]   │
│                                                 │
│  📊 Gráficos y Tablas con tus datos...         │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Pasos para Usar:

### 1. Acceder al Dashboard
```
http://localhost:3000/ml-dashboard
```

### 2. Entrenar los Modelos
- Haz clic en el botón "Entrenar Modelos"
- Espera 2-5 minutos (dependiendo de la cantidad de datos)
- Los modelos se entrenarán con TUS datos reales del ERP

### 3. Explorar los Resultados

**Tab "Segmentación de Clientes":**
- Ver gráfico de pastel con distribución
- Champions, Loyal, At Risk, Lost
- Recomendaciones por segmento

**Tab "Predicción de Churn":**
- Lista de clientes en riesgo de abandono
- Probabilidad de churn por cliente
- Acciones sugeridas

**Tab "Recomendaciones de Productos":**
- Productos que se compran juntos
- Métricas de confianza y lift
- Ideas para bundles y cross-selling

---

## 🔐 Requisitos:

✅ Debes estar **logueado** en el sistema
✅ Debes tener **datos** en tu empresa:
   - Mínimo 20 clientes
   - Mínimo 50 ventas
   - Mínimo 30 días de historial

---

## 🐛 Si No Carga:

### Error: Componente no encontrado
```bash
# Verificar que los componentes ML existan
ls frontend/src/components/ML/
# Deberías ver:
# MLDashboard.jsx
# CustomerSegmentation.jsx
# ChurnPrediction.jsx
# ProductRecommendations.jsx
```

### Error: API no disponible
```bash
# Verificar que el backend esté corriendo
curl http://localhost:8080/api/ml/models/status/
# Debería dar 401 (requiere auth) - eso es correcto
```

### Frontend no recarga
```bash
# Refrescar el navegador:
Cmd + Shift + R (Mac)
Ctrl + Shift + R (Windows)
```

---

## 📱 URLs Completas del Sistema:

| Servicio | URL |
|----------|-----|
| **Frontend** | http://localhost:3000 |
| **ML Dashboard** | http://localhost:3000/ml-dashboard |
| **Backend API** | http://localhost:8080/api/ |
| **ML APIs** | http://localhost:8080/api/ml/ |
| **Admin Django** | http://localhost:8080/admin/ |

---

## 🎨 Personalización (Opcional):

Si quieres cambiar el icono en el menú, usa cualquier icono de Material-UI:

```jsx
import { 
  Psychology,    // Cerebro
  AutoGraph,     // Gráfico automático
  Insights,      // Insights
  SmartToy,      // Robot
  TrendingUp     // Tendencia
} from '@mui/icons-material';
```

---

## 💡 Tips:

1. **Entrena los modelos regularmente** (cada semana/mes)
2. **Revisa los clientes en riesgo** para campañas de retención
3. **Usa las recomendaciones** para crear bundles de productos
4. **Exporta los resultados** para compartir con tu equipo

---

## 🎉 ¡Listo!

Ahora puedes acceder a:

```
http://localhost:3000/ml-dashboard
```

Y empezar a usar Machine Learning en tu ERP! 🚀

---

**¿Necesitas ayuda?** Consulta la documentación completa en:
- `IMPLEMENTACION_ML_MULTI_TENANT.md`
- `RESULTADOS_ML.md`
- `ML_MULTI_TENANT_RESUMEN.md`


