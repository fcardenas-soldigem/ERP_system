# 🚀 Cómo Iniciar el Servidor Django

## 🔴 Problema que tenías:

```bash
python manage.py runserver
# Error: permission denied for table django_migrations
```

**Causa:** Django intentaba conectarse con el usuario `postgres` (default en settings.py) pero la base de datos pertenece a `erp_user`.

---

## ✅ SOLUCIÓN - 3 Formas de Iniciar el Servidor:

### **Opción 1: Usar el Script Automático** ⭐ (RECOMENDADO)

He creado un script que hace todo automáticamente:

```bash
cd backend
./start_server.sh
```

¡Eso es todo! El script:
- ✅ Activa el entorno virtual
- ✅ Configura las variables de entorno
- ✅ Inicia el servidor en el puerto 8080

---

### **Opción 2: Comando Manual Completo**

```bash
cd backend
source venv/bin/activate
export DB_USER=erp_user
export DB_PASSWORD=""
python manage.py runserver 0.0.0.0:8080
```

---

### **Opción 3: Todo en Una Línea**

```bash
cd backend && source venv/bin/activate && export DB_USER=erp_user && export DB_PASSWORD="" && python manage.py runserver 0.0.0.0:8080
```

---

## 📝 Explicación de Variables de Entorno:

| Variable | Valor | Por qué |
|----------|-------|---------|
| `DB_USER` | `erp_user` | Usuario dueño de la base de datos |
| `DB_PASSWORD` | `""` (vacío) | Sin contraseña en desarrollo local |
| `DB_NAME` | `ERP_system` | Nombre de la base de datos |
| `DB_HOST` | `localhost` | (default en settings.py) |
| `DB_PORT` | `5432` | (default en settings.py) |

---

## 🔄 Para Próximas Veces:

### La forma MÁS SIMPLE:

```bash
cd /Users/renatocardenas/Desktop/ERP/ERP_system/backend
./start_server.sh
```

Y listo! 🎉

---

## 🛑 Para Detener el Servidor:

```bash
# Si está corriendo en la terminal, presiona:
Ctrl + C

# O si está en background:
lsof -ti:8080 | xargs kill -9
```

---

## ✅ Verificar que Funciona:

Abre en tu navegador:
```
http://localhost:8080/admin/
```

Deberías ver la página de login del admin de Django.

---

## 🐛 Si Sigues Teniendo Problemas:

### Error: "permission denied"
```bash
# Dar permisos otra vez
psql -U erp_user -d ERP_system -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO erp_user; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO erp_user;"
```

### Error: "command not found: python"
```bash
# Activar el entorno virtual primero
source venv/bin/activate
```

### Error: "port already in use"
```bash
# Matar proceso en puerto 8080
lsof -ti:8080 | xargs kill -9
# Luego iniciar de nuevo
./start_server.sh
```

---

## 📊 Estado Actual:

```
✅ Backend: http://localhost:8080 (FUNCIONANDO)
✅ Frontend: http://localhost:3000 (FUNCIONANDO)
✅ PostgreSQL: localhost:5432 (ACTIVO)
✅ Usuario BD: erp_user
✅ Tablas ML: CREADAS
✅ APIs ML: DISPONIBLES
```

---

## 💡 TIP para el Futuro:

Guarda este comando en un alias en tu `~/.zshrc`:

```bash
# Agregar al final de ~/.zshrc
alias erp-backend="cd /Users/renatocardenas/Desktop/ERP/ERP_system/backend && ./start_server.sh"
```

Luego solo necesitas escribir:
```bash
erp-backend
```

¡Y listo! 🚀

---

**¡Ahora tu servidor está corriendo sin problemas!** ✅


