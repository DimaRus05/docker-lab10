from flask import Flask, render_template

# Общий шаблон лежит в /storage.
app = Flask(__name__, template_folder='/storage')


# Страница открывается по / и /hello.
@app.route('/')
@app.route('/hello')
def hello_world():
    # Передаём имя приложения в шаблон.
    return render_template('index.html', source_app='app2')


if __name__ == '__main__':
    # Используем порт 8080. Режим отладки выключен.
    app.run(debug=False, host='0.0.0.0', port=8080)
