package com.uncanny.werewolf.entity;

import java.util.EnumSet;
import net.minecraft.entity.EntityType;
import net.minecraft.entity.LivingEntity;
import net.minecraft.entity.ai.goal.ActiveTargetGoal;
import net.minecraft.entity.ai.goal.Goal;
import net.minecraft.entity.ai.goal.LookAroundGoal;
import net.minecraft.entity.ai.goal.LookAtEntityGoal;
import net.minecraft.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.entity.ai.goal.RevengeGoal;
import net.minecraft.entity.ai.goal.SwimGoal;
import net.minecraft.entity.ai.goal.WanderAroundFarGoal;
import net.minecraft.entity.attribute.DefaultAttributeContainer;
import net.minecraft.entity.attribute.EntityAttributes;
import net.minecraft.entity.damage.DamageSource;
import net.minecraft.entity.data.DataTracker;
import net.minecraft.entity.data.TrackedData;
import net.minecraft.entity.data.TrackedDataHandlerRegistry;
import net.minecraft.entity.Entity;
import net.minecraft.entity.mob.HostileEntity;
import net.minecraft.entity.passive.MerchantEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.sound.SoundEvent;
import net.minecraft.sound.SoundEvents;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.World;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * A starved, too-human werewolf. It freezes and stares with a lolling head while a player looks at it,
 * and drops to all fours to sprint the moment they look away. Staring too long makes it snap and charge anyway.
 */
public class WerewolfEntity extends HostileEntity implements GeoEntity {
    private static final TrackedData<Boolean> WATCHED = DataTracker.registerData(WerewolfEntity.class, TrackedDataHandlerRegistry.BOOLEAN);

    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("animation.werewolf.idle");
    private static final RawAnimation WALK = RawAnimation.begin().thenLoop("animation.werewolf.walk");
    private static final RawAnimation RUN = RawAnimation.begin().thenLoop("animation.werewolf.run");
    private static final RawAnimation STARE = RawAnimation.begin().thenLoop("animation.werewolf.stare");
    private static final RawAnimation ATTACK = RawAnimation.begin().thenPlay("animation.werewolf.attack");

    /** Ticks a player may hold its gaze before it stops pretending and charges. */
    private static final int MAX_FROZEN_TICKS = 120;
    /** Ticks of not being watched needed before it will freeze again. */
    private static final int REARM_TICKS = 60;
    private static final double WATCH_RANGE = 40.0;

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private int watchedTicks;
    private int unwatchedTicks = REARM_TICKS;
    @Nullable
    private PlayerEntity watcher;

    public WerewolfEntity(EntityType<? extends HostileEntity> type, World world) {
        super(type, world);
        this.experiencePoints = 25;
        this.setStepHeight(1.25f);
    }

    public static DefaultAttributeContainer.Builder createAttributes() {
        return HostileEntity.createHostileAttributes()
                .add(EntityAttributes.GENERIC_MAX_HEALTH, 60.0)
                .add(EntityAttributes.GENERIC_ATTACK_DAMAGE, 9.0)
                .add(EntityAttributes.GENERIC_MOVEMENT_SPEED, 0.28)
                .add(EntityAttributes.GENERIC_FOLLOW_RANGE, 48.0)
                .add(EntityAttributes.GENERIC_ARMOR, 4.0)
                .add(EntityAttributes.GENERIC_KNOCKBACK_RESISTANCE, 0.6);
    }

    @Override
    protected void initDataTracker() {
        super.initDataTracker();
        this.dataTracker.startTracking(WATCHED, false);
    }

    @Override
    protected void initGoals() {
        this.goalSelector.add(0, new SwimGoal(this));
        this.goalSelector.add(1, new FreezeWhenWatchedGoal());
        this.goalSelector.add(2, new MeleeAttackGoal(this, 1.7, true));
        this.goalSelector.add(5, new WanderAroundFarGoal(this, 0.8));
        // chance 1.0: if a player is near, it is always looking at them
        this.goalSelector.add(6, new LookAtEntityGoal(this, PlayerEntity.class, 24.0f, 1.0f));
        this.goalSelector.add(7, new LookAroundGoal(this));
        this.targetSelector.add(1, new RevengeGoal(this));
        this.targetSelector.add(2, new ActiveTargetGoal<>(this, PlayerEntity.class, true));
        this.targetSelector.add(3, new ActiveTargetGoal<>(this, MerchantEntity.class, false));
    }

    public boolean isWatched() {
        return this.dataTracker.get(WATCHED);
    }

    @Override
    protected void mobTick() {
        super.mobTick();
        PlayerEntity staring = findStaringPlayer();
        if (staring != null && unwatchedTicks >= REARM_TICKS && watchedTicks < MAX_FROZEN_TICKS) {
            watchedTicks++;
            watcher = staring;
            if (watchedTicks == MAX_FROZEN_TICKS) {
                // it has had enough of being looked at
                this.playSound(SoundEvents.ENTITY_VILLAGER_HURT, 2.0f, 0.35f);
                this.playSound(SoundEvents.ENTITY_WOLF_GROWL, 2.0f, 0.5f);
                this.setTarget(staring);
                unwatchedTicks = 0;
            }
        } else {
            if (staring == null) {
                unwatchedTicks++;
                watchedTicks = 0;
            }
            watcher = null;
        }
        this.dataTracker.set(WATCHED, watcher != null);
    }

    @Nullable
    private PlayerEntity findStaringPlayer() {
        PlayerEntity best = null;
        double bestDist = Double.MAX_VALUE;
        for (PlayerEntity player : this.getWorld().getPlayers()) {
            if (player.isSpectator() || !player.isAlive()) {
                continue;
            }
            double dist = this.squaredDistanceTo(player);
            if (dist < WATCH_RANGE * WATCH_RANGE && dist < bestDist && isPlayerStaring(player)) {
                best = player;
                bestDist = dist;
            }
        }
        return best;
    }

    private boolean isPlayerStaring(PlayerEntity player) {
        Vec3d look = player.getRotationVec(1.0f).normalize();
        Vec3d toMe = new Vec3d(this.getX() - player.getX(), this.getBodyY(0.6) - player.getEyeY(), this.getZ() - player.getZ());
        double len = toMe.length();
        if (len < 1.0e-3) {
            return true;
        }
        // a fairly wide cone: it notices being looked at, not just being aimed at
        return look.dotProduct(toMe.multiply(1.0 / len)) > 0.88 && player.canSee(this);
    }

    @Override
    public boolean tryAttack(Entity target) {
        boolean hit = super.tryAttack(target);
        if (hit) {
            this.triggerAnim("attack", "attack");
        }
        return hit;
    }

    // --- sounds: it mimics villagers, badly ---------------------------------------------------

    @Override
    protected SoundEvent getAmbientSound() {
        return this.random.nextInt(3) == 0 ? SoundEvents.ENTITY_WOLF_GROWL : SoundEvents.ENTITY_VILLAGER_AMBIENT;
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source) {
        return SoundEvents.ENTITY_VILLAGER_HURT;
    }

    @Override
    protected SoundEvent getDeathSound() {
        return SoundEvents.ENTITY_WOLF_HOWL;
    }

    @Override
    public float getSoundPitch() {
        return 0.5f + this.random.nextFloat() * 0.12f;
    }

    @Override
    public int getMinAmbientSoundDelay() {
        return 160;
    }

    @Override
    public boolean canTarget(LivingEntity target) {
        return super.canTarget(target) && !(target instanceof WerewolfEntity);
    }

    // --- GeckoLib -----------------------------------------------------------------------------

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "movement", 3, this::movementState));
        controllers.add(new AnimationController<>(this, "attack", 2, state -> PlayState.STOP)
                .triggerableAnim("attack", ATTACK));
    }

    private PlayState movementState(AnimationState<WerewolfEntity> state) {
        if (this.isWatched()) {
            return state.setAndContinue(STARE);
        }
        if (state.isMoving()) {
            // MeleeAttackGoal sets the synced "attacking" flag while it chases
            return state.setAndContinue(this.isAttacking() ? RUN : WALK);
        }
        return state.setAndContinue(IDLE);
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    /** Holds perfectly still and keeps its eyes on whoever is looking at it. */
    private class FreezeWhenWatchedGoal extends Goal {
        FreezeWhenWatchedGoal() {
            this.setControls(EnumSet.of(Control.MOVE, Control.JUMP, Control.LOOK));
        }

        @Override
        public boolean canStart() {
            return watcher != null;
        }

        @Override
        public boolean shouldContinue() {
            return watcher != null;
        }

        @Override
        public void start() {
            getNavigation().stop();
        }

        @Override
        public void tick() {
            getNavigation().stop();
            setVelocity(0.0, getVelocity().y, 0.0);
            if (watcher != null) {
                getLookControl().lookAt(watcher, 10.0f, 10.0f);
            }
        }
    }
}
