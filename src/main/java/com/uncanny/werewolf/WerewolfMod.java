package com.uncanny.werewolf;

import com.uncanny.werewolf.entity.WerewolfEntity;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.biome.v1.BiomeModifications;
import net.fabricmc.fabric.api.biome.v1.BiomeSelectors;
import net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;
import net.fabricmc.fabric.api.object.builder.v1.entity.FabricEntityTypeBuilder;
import net.minecraft.entity.EntityDimensions;
import net.minecraft.entity.EntityType;
import net.minecraft.entity.SpawnGroup;
import net.minecraft.entity.SpawnRestriction;
import net.minecraft.entity.mob.HostileEntity;
import net.minecraft.item.Item;
import net.minecraft.item.ItemGroups;
import net.minecraft.item.SpawnEggItem;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.registry.tag.BiomeTags;
import net.minecraft.util.Identifier;
import net.minecraft.world.Heightmap;

public class WerewolfMod implements ModInitializer {
    public static final String MOD_ID = "uncanny_werewolf";

    public static final EntityType<WerewolfEntity> WEREWOLF = Registry.register(
            Registries.ENTITY_TYPE,
            id("werewolf"),
            FabricEntityTypeBuilder.createMob()
                    .spawnGroup(SpawnGroup.MONSTER)
                    .entityFactory(WerewolfEntity::new)
                    .dimensions(EntityDimensions.fixed(1.0f, 2.9f))
                    .trackRangeBlocks(80)
                    .defaultAttributes(WerewolfEntity::createAttributes)
                    .spawnRestriction(SpawnRestriction.Location.ON_GROUND,
                            Heightmap.Type.MOTION_BLOCKING_NO_LEAVES, HostileEntity::canSpawnInDark)
                    .build());

    public static final Item WEREWOLF_SPAWN_EGG = Registry.register(
            Registries.ITEM,
            id("werewolf_spawn_egg"),
            new SpawnEggItem(WEREWOLF, 0x3a332e, 0xcdbfb5, new Item.Settings()));

    public static Identifier id(String path) {
        return new Identifier(MOD_ID, path);
    }

    @Override
    public void onInitialize() {
        ItemGroupEvents.modifyEntriesEvent(ItemGroups.SPAWN_EGGS).register(entries -> entries.add(WEREWOLF_SPAWN_EGG));

        // Rare night spawns in forests and taigas.
        BiomeModifications.addSpawn(
                BiomeSelectors.tag(BiomeTags.IS_FOREST).or(BiomeSelectors.tag(BiomeTags.IS_TAIGA)),
                SpawnGroup.MONSTER, WEREWOLF, 5, 1, 1);
    }
}
