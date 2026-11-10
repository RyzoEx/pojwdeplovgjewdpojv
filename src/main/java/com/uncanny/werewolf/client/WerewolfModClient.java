package com.uncanny.werewolf.client;

import com.uncanny.werewolf.WerewolfMod;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;

public class WerewolfModClient implements ClientModInitializer {
    @Override
    public void onInitializeClient() {
        EntityRendererRegistry.register(WerewolfMod.WEREWOLF, WerewolfRenderer::new);
    }
}
