<template>
    <div>
        <div>
            <v-select label="Data" :items="data_att_items" v-model="data_att_selected" hide-details class="margin-bottom: 16px"/>
        </div>
        <div>
            <v-switch label="Plot as steps" v-model="as_steps" />
        </div>
        <div>
            <v-subheader class="pl-0 slider-label">opacity</v-subheader>
            <glue-throttled-slider wait="300" max="1" step="0.01" :value.sync="glue_state.alpha" hide-details />
        </div>
    </div>
</template>
<script>
    modules.export = {
        methods: {
            /* TODO: use @change with debounce instead of @end */
            setAlpha(value) {
                this.glue_state.alpha = value;
            },
        },
    }
</script>

