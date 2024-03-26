from ipyvuetify import VuetifyTemplate
import traitlets
from glue_jupyter.vuetify_helpers import link_glue_choices, link_glue
from glue_jupyter.state_traitlets_helpers import GlueState

__all__ = ['TracesLayerStateWidget']


class TracesLayerStateWidget(VuetifyTemplate):
    template_file = (__file__, 'layer_traces.vue')

    glue_state = GlueState().tag(sync=True)
    markers_visible = traitlets.Bool(False).tag(sync=True)

    def __init__(self, layer_state):
        super().__init__()

        self.glue_state = layer_state

        link_glue(self, 'markers_visible', layer_state)
