package com.uncanny.werewolf.client;

import com.uncanny.werewolf.entity.WerewolfEntity;
import net.minecraft.client.render.entity.EntityRendererFactory;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

public class WerewolfRenderer extends GeoEntityRenderer<WerewolfEntity> {
    public WerewolfRenderer(EntityRendererFactory.Context context) {
        super(context, new WerewolfModel());
        this.shadowRadius = 0.8f;
        // werewolf_glowmask.png: the eyes catch light like an animal's
        addRenderLayer(new AutoGlowingGeoLayer<>(this));
    }
}
