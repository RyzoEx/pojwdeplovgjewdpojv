package com.uncanny.werewolf;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.loading.json.raw.Model;
import software.bernie.geckolib.loading.object.BakedAnimations;
import software.bernie.geckolib.loading.object.BakedModelFactory;
import software.bernie.geckolib.loading.object.GeometryTree;
import software.bernie.geckolib.util.JsonUtil;

/** Parses the generated assets with GeckoLib's own loaders, exactly as the client resource reload does. */
class AssetLoadingTest {
    private static final String ROOT = "/assets/uncanny_werewolf/";

    private static Reader open(String path) {
        return new InputStreamReader(AssetLoadingTest.class.getResourceAsStream(ROOT + path), StandardCharsets.UTF_8);
    }

    @Test
    void geometryBakes() throws Exception {
        Model model;
        try (Reader r = open("geo/entity/werewolf.geo.json")) {
            model = JsonUtil.GEO_GSON.fromJson(r, Model.class);
        }
        BakedGeoModel baked = BakedModelFactory.getForNamespace(WerewolfMod.MOD_ID).constructGeoModel(GeometryTree.fromModel(model));
        List<GeoBone> all = new ArrayList<>();
        collect(baked.topLevelBones(), all);
        assertEquals(49, all.size());
        int cubes = all.stream().mapToInt(b -> b.getCubes().size()).sum();
        assertEquals(145, cubes);
        assertTrue(all.stream().anyMatch(b -> b.getName().equals("head_look")));
        assertTrue(baked.getBone("jaw").isPresent());
    }

    @Test
    void animationsLoad() throws Exception {
        JsonObject root;
        try (Reader r = open("animations/entity/werewolf.animation.json")) {
            root = JsonParser.parseReader(r).getAsJsonObject();
        }
        BakedAnimations anims = JsonUtil.GEO_GSON.fromJson(root.getAsJsonObject("animations"), BakedAnimations.class);
        for (String name : Set.of("idle", "walk", "run", "attack", "stare")) {
            assertNotNull(anims.getAnimation("animation.werewolf." + name), name);
        }
        assertEquals(1.0, anims.getAnimation("animation.werewolf.attack").length() / 20.0, 1e-6);
    }

    private static void collect(List<GeoBone> bones, List<GeoBone> out) {
        for (GeoBone b : bones) {
            out.add(b);
            collect(b.getChildBones(), out);
        }
    }
}
