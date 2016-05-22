def init_plotly_offline_mode():
    from IPython.display import display_javascript
    import shutil
    from plotly import offline
    from os import path
    offline.offline.__PLOTLY_OFFLINE_INITIALIZED = True
    shutil.copy(path.join(offline.__path__[0], "plotly.min.js"), ".")

    jscode = """
    require.config({
      paths: {
        plotly: "/files/" + Jupyter.notebook.notebook_path + "/../" + "plotly.min"
      },

      shim: {
        plotly: {
          deps: [],
          exports: 'plotly'
        }
      }
    });

    require(['plotly'], function(plotly) {
        window.Plotly = plotly;
        console.log("Plotly loaded");
    });
    """
    display_javascript(jscode, raw=True)

    
def init_plotly_online_mode():
    from IPython.display import display_javascript
    from plotly import offline
    offline.offline.__PLOTLY_OFFLINE_INITIALIZED = True
    jscode = """
    require.config({
      paths: {
        d3: 'http://cdnjs.cloudflare.com/ajax/libs/d3/3.5.16/d3.min',
        plotly: 'http://cdn.plot.ly/plotly-1.10.0.min',
        jquery: 'https://code.jquery.com/jquery-migrate-1.4.1.min'
      },

      shim: {
        plotly: {
          deps: ['d3', 'jquery'],
          exports: 'plotly'
        }
      }
    });

    require(['d3', 'plotly'], function(d3, plotly) {
        window.Plotly = plotly;
    });
    """
    display_javascript(jscode, raw=True)
    
from jinja2 import Template

JsTemplate = Template("""
<script>
(function(){
var comm_manager=Jupyter.notebook.kernel.comm_manager;

comm_manager.register_target('{{uid}}', function(comm, msg){
    console.log(msg);
    var data = JSON.parse(msg.content.data.data);
    var code = msg.content.data.code;
    var graph = document.getElementById("{{uid}}");
    eval(code);
    Plotly.redraw(graph);
});

var send = function(msg){
    var comm = comm_manager.new_comm("{{uid}}", msg);
    comm.close();
};

require(["plotly"], function(Plotly){
    var graph = document.getElementById("{{uid}}");
    {%if onclick%}
    graph.on("plotly_click", function(data){
        if(typeof(data) == "undefined") return;
        if(!data.hasOwnProperty("lassoPoints")){
            var points = _.map(data.points, function(p){
                return {
                  curveNumber:p.curveNumber,
                  pointNumber:p.pointNumber,
                  x:p.x, y:p.y};
            });
            var send_data = {"event":"select", "data":{"select_type":"click", "points":points}};
            console.log(send_data);
            send(send_data);
        }
    });
    {% endif %}

    {%if onrelayout %}
    graph.on("plotly_relayout", function(data){
        var send_data = {"event":"relayout", "data":data};
        console.log(send_data);
        send(send_data);
    });
    {% endif %}
});

})();

</script>
""")

from ipywidgets import HTML
from plotly.offline.offline import _plot_html
from ipykernel.comm import Comm
from bokeh.core import json_encoder

class PlotlyWidget(HTML):

    def __init__(self, figure, click_callback=None, relayout_callback=None, **kwargs):
        super().__init__(**kwargs)
        html, uid, _, _ = _plot_html(figure, False, "", True, None, None, True) #{1}
        self.uid = str(uid)
        jscode = JsTemplate.render(
            uid=self.uid,
            onclick=click_callback is not None,
            onrelayout=relayout_callback is not None)
        html += jscode  #{2}
        self.value = html  #{3}
        self.click_callback = click_callback
        self.relayout_callback = relayout_callback
        self.comm_manager.register_target(self.uid, self._on_open) #{4}

    @property
    def comm_manager(self):
        return get_ipython().kernel.comm_manager

    def _on_open(self, comm, msg):
        data = msg["content"]["data"]
        event = data["event"]
        if event == "select" and self.click_callback is not None:
            self.click_callback(data["data"])
        elif event == "relayout" and self.relayout_callback is not None:
            self.relayout_callback(data["data"])
        self.recv_msg = msg

    def send(self, code, data): #{5}
        comm = Comm(target_name=str(self.uid),
                    data={"code":code, "data":json_encoder.serialize_json(data)})
        comm.close()
