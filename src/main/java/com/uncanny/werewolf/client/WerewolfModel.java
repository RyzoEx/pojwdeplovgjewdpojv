package com.uncanny.werewolf.client;

import com.uncanny.werewolf.WerewolfMod;
import com.uncanny.werewolf.entity.WerewolfEntity;
import net.minecraft.util.math.MathHelper;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.state.BoneSnapshot;
import software.bernie.geckolib.model.DefaultedEntityGeoModel;
import software.bernie.geckolib.model.data.EntityModelData;

public class WerewolfModel extends DefaultedEntityGeoModel<WerewolfEntity> {
    public WerewolfModel() {
        super(WerewolfMod.id("werewolf"));
    }

    @Override
    public void setCustomAnimations(WerewolfEntity animatable, long instanceId, AnimationState<WerewolfEntity> animationState) {
        super.setCustomAnimations(animatable, instanceId, animationState);
        // "head_look" sits under a levelled bone and is never keyframed, so head tracking composes with the
        // animated "head" (tilts, twitches) instead of overwriting it.
        CoreGeoBone look = getAnimationProcessor().getBone("head_look");
        if (look == null) {
            return;
        }
        EntityModelData data = animationState.getData(DataTickets.ENTITY_MODEL_DATA);
        BoneSnapshot initial = look.getInitialSnapshot();
        look.setRotX(initial.getRotX() + data.headPitch() * MathHelper.RADIANS_PER_DEGREE);
        look.setRotY(initial.getRotY() + data.netHeadYaw() * MathHelper.RADIANS_PER_DEGREE);
    }
}
