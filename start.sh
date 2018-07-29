#gunicorn --bind 127.0.0.1:5001 --log-level info --pythonpath './sh_face_rec/' -k gevent --preload sh_face_rec.startserver:app
uwsgi uwsgi_start.ini