<template>
    <div>
        <div>
            <v-select :items="colormap_att_items" label="color" v-model="colormap_att_selected"/>
            </v-select>
        </div>
        <div>
            <v-select :items="colormap_name_items" label="colormap_name" v-model="colormap_name_selected"/>
            </v-select>   
        </div>
    </div>
</template>
<script>
    module.exports = {
    }
</script>
<style>
    .v-navigation-drawer {
    z-index: 999999 !important;
    }
</style>