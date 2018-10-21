from werkzeug.contrib.profiler import ProfilerMiddleware
from flask.ext.sqlalchemy import get_debug_queries
from flask_debugtoolbar import DebugToolbarExtension
from liaison import app
from flask import jsonify

@app.route('/routes', methods = ['GET'])
def help():
    """Print available functions."""
    func_list = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            func_list[rule.rule] = app.view_functions[rule.endpoint].__doc__
    return jsonify(func_list)

@app.route('/err', methods = ['GET'])
def error_out():
    raise 1/0
    return jsonify({})


DATABASE_QUERY_TIMEOUT = 0.2

@app.after_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= DATABASE_QUERY_TIMEOUT:
            app.logger.warning("\n\n\nSLOW QUERY: %s\nParameters: %s\nDuration: %fs\nContext: %s\n" % (query.statement, query.parameters, query.duration, query.context))
    return response

toolbar = DebugToolbarExtension(app)
toolbar.init_app(app)
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.run(host='0.0.0.0', port=5000, debug=True)

