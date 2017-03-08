# Scraper [Registro Sanitario ISPCh](http://registrosanitario.ispch.gob.cl/)
Este script descarga información de los medicamentos publicados en el registro sanitario del Instituto de Salud Pública de Chile, utilizando bs4 para extraer los datos de HTML y multithreading para disminuir los tiempos de ejecución

## Instalación

```
git clone git@github.com:hopazo/scrapers-salud
cd scrapers-salud
pip install -r requirements.txt
```

## Uso

```
python ipsch-registro-sanitario.py [--venta (directa | receta-medica | receta-cheque | receta-retenida)] [--estado (vigente | no-vigente | suspendido)] [--threads N]
```

## Contribuciones
1. Hacer un fork
2. Crear tu feature branch: `git checkout -b nueva-feature`
3. Commitear tus cambios: `git commit -am 'Agregar nueva feature'`
4. Pushear a tu branch: `git push origin nueva-feature`
5. Hacer un pull request :D

## Authors
* **Héctor Opazo** - [hopazo](https://github.com/hopazo)

## Creditos
* *Álvaro Bustamante* - [vareta](https://github.com/Vareta) por realizar la implementación funcional monohilo sin la que hubiese sido considerablemente más dificil realizar esta versión
* Este demo fue desarrollado a partir del trabajo realizado para [PRED SpA](http://www.pred.cl)
