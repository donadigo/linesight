import importlib
import random
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import torch
from torch.utils.tensorboard import SummaryWriter

import trackmania_rl.agents.iqn as iqn
from trackmania_rl import buffer_management, misc, nn_utilities, tm_interface_manager
from trackmania_rl.experience_replay.basic_experience_replay import BasicExperienceReplay

base_dir = Path(__file__).resolve().parents[1]

run_name = "51"
map_name = "map5"
good_time_save_all_ms = 129000
zone_centers = np.load(str(base_dir / "maps" / f"{map_name}_{misc.distance_between_checkpoints}m.npy"))

for i in range(misc.n_zone_centers_in_inputs):
    zone_centers = np.vstack(
        (
            zone_centers,
            (2 * zone_centers[-1] - zone_centers[-2])[None, :],
        )
    )

save_dir = base_dir / "save" / run_name
save_dir.mkdir(parents=True, exist_ok=True)
tensorboard_writer = SummaryWriter(log_dir=str(base_dir / "tensorboard" / run_name))

layout = {
    "92": {
        "eval_race_time": [
            "Multiline",
            [
                "eval_race_time$",
            ],
        ],
        "eval_race_time_finished": [
            "Multiline",
            [
                "eval_race_time_finished",
            ],
        ],
        "explo_race_time": [
            "Multiline",
            [
                "explo_race_time$",
            ],
        ],
        "explo_race_time_finished": [
            "Multiline",
            [
                "explo_race_time_finished",
            ],
        ],
        "eval_q_values_starting_frame": [
            "Multiline",
            [f"eval_q_value_{i}_starting_frame" for i in range(len(misc.inputs))],
        ],
        "race_time": [
            "Multiline",
            [
                "last100_min_race_time",
                "last100_d1_race_time",
                "last100_median_race_time",
                "last100_d9_race_time",
            ],
        ],
        r"last100_%race finished": ["Multiline", [r"last100_%race finished"]],
        "loss": ["Multiline", ["laststep_mean_loss$", "laststep_mean_loss_test"]],
        "noisy_std": [
            "Multiline",
            [f"std_due_to_noisy_for_action{i}" for i in range(len(misc.inputs))],
        ],
        "iqn_std": [
            "Multiline",
            [f"std_within_iqn_quantiles_for_action{i}" for i in range(len(misc.inputs))],
        ],
        "laststep_race_time_ratio": ["Multiline", ["laststep_race_time_ratio"]],
        "race_time_with_eval": [
            "Multiline",
            [
                "last100_min_race_time",
                "eval_race_time",
                "last100_d1_race_time",
                "last100_median_race_time",
                "last100_d9_race_time",
            ],
        ],
        "zone_reached": [
            "Multiline",
            [
                "last100_d1_zone_reached",
                "last100_median_zone_reached",
                "last100_d9_zone_reached",
            ],
        ],
        "single_zone_reached": [
            "Multiline",
            [
                "single_zone_reached",
            ],
        ],
        "mean_action_gap": [
            "Multiline",
            [
                "mean_action_gap",
            ],
        ],
        "layer_L2": [
            "Multiline",
            [
                "layer_.*_L2",
            ],
        ],
    },
}
tensorboard_writer.add_custom_scalars(layout)

# noinspection PyUnresolvedReferences
torch.backends.cudnn.benchmark = True
random_seed = 444
torch.cuda.manual_seed_all(random_seed)
torch.manual_seed(random_seed)
random.seed(random_seed)
np.random.seed(random_seed)

# ========================================================
# Create new stuff
# ========================================================
model1 = torch.jit.script(
    iqn.Agent(
        float_inputs_dim=misc.float_input_dim,
        float_hidden_dim=misc.float_hidden_dim,
        conv_head_output_dim=misc.conv_head_output_dim,
        dense_hidden_dimension=misc.dense_hidden_dimension,
        iqn_embedding_dimension=misc.iqn_embedding_dimension,
        n_actions=len(misc.inputs),
        float_inputs_mean=misc.float_inputs_mean,
        float_inputs_std=misc.float_inputs_std,
    )
).to("cuda")
model2 = torch.jit.script(
    iqn.Agent(
        float_inputs_dim=misc.float_input_dim,
        float_hidden_dim=misc.float_hidden_dim,
        conv_head_output_dim=misc.conv_head_output_dim,
        dense_hidden_dimension=misc.dense_hidden_dimension,
        iqn_embedding_dimension=misc.iqn_embedding_dimension,
        n_actions=len(misc.inputs),
        float_inputs_mean=misc.float_inputs_mean,
        float_inputs_std=misc.float_inputs_std,
    )
).to("cuda")
print(model1)

optimizer1 = torch.optim.RAdam(model1.parameters(), lr=misc.learning_rate)
# optimizer1 = torch.optim.SGD(model1.parameters(), lr=misc.learning_rate, momentum=0.8)
scaler = torch.cuda.amp.GradScaler()
buffer = BasicExperienceReplay(capacity=misc.memory_size)
buffer_test = BasicExperienceReplay(capacity=int(misc.memory_size * misc.buffer_test_ratio))
fast_stats_tracker = defaultdict(list)
step_stats_history = []
# ========================================================
# Load existing stuff
# ========================================================
# noinspection PyBroadException
try:
    model1.load_state_dict(torch.load(save_dir / "weights1.torch"))
    model2.load_state_dict(torch.load(save_dir / "weights2.torch"))
    optimizer1.load_state_dict(torch.load(save_dir / "optimizer1.torch"))
    print(" =========================     Weights loaded !     ================================")
except:
    # FIXME UNDO FOR RUN 13
    # with torch.no_grad():
    #     model1.A_head[2].bias_mu *= 0
    #     model2.A_head[2].bias_mu *= 0
    #     # model1.A_head[2].bias_mu += torch.as_tensor([2.5, 2, 2, 1, 1, 1, 0, 0, 0, -1, -1, -1], device="cuda")
    #     # model2.A_head[2].bias_mu += torch.as_tensor([2.5, 2, 2, 1, 1, 1, 0, 0, 0, -1, -1, -1], device="cuda")
    #     model1.A_head[2].bias_mu += torch.as_tensor(
    #         [-2, -2.5, -2.5, -3, -3, -3, -4, -4, -4], device="cuda"
    #     )
    #     model2.A_head[2].bias_mu += torch.as_tensor(
    #         [-2, -2.5, -2.5, -3, -3, -3, -4, -4, -4], device="cuda"
    #     )
    print(" Could not load weights")

# noinspection PyBroadException
try:
    step_stats_history = joblib.load(save_dir / "step_stats_history.joblib")
    fast_stats_tracker = joblib.load(save_dir / "fast_stats_tracker.joblib")
    print(" =========================      Stats loaded !      ================================")
except:
    print(" Could not load stats")

# ========================================================
# Bring back relevant training history
# ========================================================
if len(step_stats_history) == 0:
    # No history, start from scratch
    cumul_number_frames_played = 0
    cumul_number_memories_generated = 0
    cumul_training_hours = 0
    cumul_number_batches_done = 0
    cumul_number_target_network_updates = 0
else:
    # Use previous known cumulative counters
    cumul_number_frames_played = step_stats_history[-1]["cumul_number_frames_played"]
    cumul_number_memories_generated = step_stats_history[-1]["cumul_number_memories_generated"]
    cumul_training_hours = step_stats_history[-1]["cumul_training_hours"]
    cumul_number_batches_done = step_stats_history[-1]["cumul_number_batches_done"]
    cumul_number_target_network_updates = step_stats_history[-1]["cumul_number_target_network_updates"]

    # cumul_number_batches_done = (misc.number_times_single_memory_is_used_before_discard * (cumul_number_memories_generated - misc.virtual_memory_size_start_learn)) // misc.batch_size
    # cumul_number_target_network_updates =  (cumul_number_batches_done * misc.batch_size) //  misc.number_memories_trained_on_between_target_network_updates

number_frames_played = 0
number_memories_generated = 0

# ========================================================
# Make the trainer
# ========================================================
trainer = iqn.Trainer(
    model=model1,
    model2=model2,
    optimizer=optimizer1,
    scaler=scaler,
    batch_size=misc.batch_size,
    iqn_k=misc.iqn_k,
    iqn_n=misc.iqn_n,
    iqn_kappa=misc.iqn_kappa,
    epsilon=misc.epsilon,
    epsilon_boltzmann=misc.epsilon_boltzmann,
    gamma=misc.gamma,
    AL_alpha=misc.AL_alpha,
    tau_epsilon_boltzmann=misc.tau_epsilon_boltzmann,
    tau_greedy_boltzmann=misc.tau_greedy_boltzmann,
)

# ========================================================
# Training loop
# ========================================================
model1.train()
time_next_save = time.time() + misc.statistics_save_period_seconds
tmi = tm_interface_manager.TMInterfaceManager(
    base_dir=base_dir,
    running_speed=misc.running_speed,
    run_steps_per_action=misc.tm_engine_step_per_action,
    max_overall_duration_ms=misc.max_overall_duration_ms,
    max_minirace_duration_ms=misc.max_minirace_duration_ms,
    interface_name="TMInterface0",
    zone_centers=zone_centers,
)

for kk in range(5):
    cumul_number_frames_played += 1
    # ===============================================
    #   PLAY ONE ROUND
    # ===============================================
    rollout_start_time = time.time()
    trainer.epsilon = 0
    trainer.epsilon_boltzmann = 0
    trainer.gamma = misc.gamma
    trainer.AL_alpha = misc.AL_alpha
    trainer.tau_epsilon_boltzmann = misc.tau_epsilon_boltzmann
    trainer.tau_greedy_boltzmann = misc.tau_greedy_boltzmann
    for param_group in optimizer1.param_groups:
        param_group["lr"] = misc.learning_rate
    rollout_results = tmi.rollout(
        exploration_policy=trainer.get_exploration_action,
        stats_tracker=fast_stats_tracker,
        is_eval=True,
    )
    number_frames_played += len(rollout_results["frames"])
    fast_stats_tracker["race_time_ratio"].append(
        fast_stats_tracker["race_time_for_ratio"][-1] / ((time.time() - rollout_start_time) * 1000)
    )
    fast_stats_tracker["zone_reached"].append(len(rollout_results["zone_entrance_time_ms"]) - 1)

    tensorboard_writer.add_scalar(
        tag="explo_race_time",
        scalar_value=fast_stats_tracker["race_time"][-1] / 1000,
        walltime=time.time(),
    )
    tensorboard_writer.add_scalar(
        tag="mean_action_gap",
        scalar_value=-(
            np.array(rollout_results["q_values"]) - np.array(rollout_results["q_values"]).max(axis=1, initial=None).reshape(-1, 1)
        ).mean(),
        walltime=time.time(),
    )
    if fast_stats_tracker["race_finished"][-1]:
        tensorboard_writer.add_scalar(
            tag="explo_race_time_finished",
            scalar_value=fast_stats_tracker["race_time"][-1] / 1000,
            walltime=time.time(),
        )

    tensorboard_writer.add_scalar(
        tag="single_zone_reached",
        scalar_value=fast_stats_tracker["zone_reached"][-1],
        walltime=time.time(),
    )
    print("race time ratio  ", np.median(np.array(fast_stats_tracker["race_time_ratio"])))

    # (
    #     buffer,
    #     buffer_test,
    #     number_memories_added,
    # ) = buffer_management.fill_buffer_from_rollout_with_n_steps_rule(
    #     buffer,
    #     buffer_test,
    #     rollout_results,
    #     misc.n_steps,
    #     misc.gamma,
    #     misc.discard_non_greedy_actions_in_nsteps,
    #     misc.n_zone_centers_in_inputs,
    #     zone_centers,
    # )
    #
    # number_memories_generated += number_memories_added
    # cumul_number_memories_generated += number_memories_added
    # print(f" NMG={cumul_number_memories_generated:<8}")

    # ===============================================
    #   STATISTICS EVERY NOW AND THEN
    # ===============================================

    cumul_training_hours += misc.statistics_save_period_seconds / 3600

    # ===============================================
    #   FILL STEPS STATS HISTORY
    # ===============================================
    step_stats = {
        "number_frames_played": number_frames_played,
        "number_memories_generated": number_memories_generated,
        "training_hours": misc.statistics_save_period_seconds / 3600,
        "cumul_number_frames_played": cumul_number_frames_played,
        "cumul_number_memories_generated": cumul_number_memories_generated,
        "cumul_training_hours": cumul_training_hours,
        "cumul_number_batches_done": cumul_number_batches_done,
        "cumul_number_target_network_updates": cumul_number_target_network_updates,
        "gamma": misc.gamma,
        "n_steps": misc.n_steps,
        "epsilon": trainer.epsilon,
        "epsilon_boltzmann": trainer.epsilon_boltzmann,
        "tau_epsilon_boltzmann": trainer.tau_epsilon_boltzmann,
        "tau_greedy_boltzmann": trainer.tau_greedy_boltzmann,
        "AL_alpha": trainer.AL_alpha,
        "learning_rate": misc.learning_rate,
        "discard_non_greedy_actions_in_nsteps": misc.discard_non_greedy_actions_in_nsteps,
        "reward_per_ms_velocity": misc.reward_per_ms_velocity,
        "reward_per_ms_press_forward": misc.reward_per_ms_press_forward,
        # "reward_bogus_low_speed": misc.reward_bogus_low_speed,
        #
        r"last100_%race finished": np.array(fast_stats_tracker["race_finished"][-100:]).mean(),
        r"last100_%light_desynchro": np.array(fast_stats_tracker["n_ors_light_desynchro"][-100:]).sum()
        / (np.array(fast_stats_tracker["race_time"][-100:]).sum() / (misc.ms_per_tm_engine_step * misc.tm_engine_step_per_action)),
        r"last100_%consecutive_frames_equal": np.array(fast_stats_tracker["n_two_consecutive_frames_equal"][-100:]).sum()
        / (np.array(fast_stats_tracker["race_time"][-100:]).sum() / (misc.ms_per_tm_engine_step * misc.tm_engine_step_per_action)),
        #
        "laststep_mean_loss": np.array(fast_stats_tracker["loss"]).mean(),
        "laststep_mean_loss_test": np.array(fast_stats_tracker["loss_test"]).mean(),
        "laststep_n_tmi_protection": np.array(fast_stats_tracker["n_frames_tmi_protection_triggered"]).sum(),
        "laststep_race_time_ratio": np.median(np.array(fast_stats_tracker["race_time_ratio"])),
        "laststep_train_on_batch_duration": np.median(np.array(fast_stats_tracker["train_on_batch_duration"])),
        #
        "laststep_time_to_answer_normal_step": np.median(np.array(fast_stats_tracker["time_to_answer_normal_step"])),
        "laststep_time_to_answer_action_step": np.median(np.array(fast_stats_tracker["time_to_answer_action_step"])),
        "laststep_time_between_normal_on_run_steps": np.median(np.array(fast_stats_tracker["time_between_normal_on_run_steps"])),
        "laststep_time_between_action_on_run_steps": np.median(np.array(fast_stats_tracker["time_between_action_on_run_steps"])),
        "laststep_time_to_grab_frame": np.median(np.array(fast_stats_tracker["time_to_grab_frame"])),
        "laststep_time_between_grab_frame": np.median(np.array(fast_stats_tracker["time_between_grab_frame"])),
        "laststep_time_A_rgb2gray": np.median(np.array(fast_stats_tracker["time_A_rgb2gray"])),
        "laststep_time_A_geometry": np.median(np.array(fast_stats_tracker["time_A_geometry"])),
        "laststep_time_A_stack": np.median(np.array(fast_stats_tracker["time_A_stack"])),
        "laststep_time_exploration_policy": np.median(np.array(fast_stats_tracker["time_exploration_policy"])),
        "laststep_time_to_iface_set_set": np.median(np.array(fast_stats_tracker["time_to_iface_set_set"])),
        "laststep_time_after_iface_set_set": np.median(np.array(fast_stats_tracker["time_after_iface_set_set"])),
        #
        "last100_min_race_time": np.array(fast_stats_tracker["race_time"][-100:]).min(initial=None) / 1000,
        "last100_d1_race_time": np.quantile(np.array(fast_stats_tracker["race_time"][-100:]), 0.1) / 1000,
        "last100_q1_race_time": np.quantile(np.array(fast_stats_tracker["race_time"][-100:]), 0.25) / 1000,
        "last100_median_race_time": np.quantile(np.array(fast_stats_tracker["race_time"][-100:]), 0.5) / 1000,
        "last100_q3_race_time": np.quantile(np.array(fast_stats_tracker["race_time"][-100:]), 0.75) / 1000,
        "last100_d9_race_time": np.quantile(np.array(fast_stats_tracker["race_time"][-100:]), 0.9) / 1000,
        #
        "last100_d1_value_starting_frame": np.quantile(np.array(fast_stats_tracker["value_starting_frame"][-100:]), 0.1),
        "last100_q1_value_starting_frame": np.quantile(np.array(fast_stats_tracker["value_starting_frame"][-100:]), 0.25),
        "last100_median_value_starting_frame": np.quantile(np.array(fast_stats_tracker["value_starting_frame"][-100:]), 0.5),
        "last100_q3_value_starting_frame": np.quantile(np.array(fast_stats_tracker["value_starting_frame"][-100:]), 0.75),
        "last100_d9_value_starting_frame": np.quantile(np.array(fast_stats_tracker["value_starting_frame"][-100:]), 0.9),
        #
        "last100_d1_zone_reached": np.quantile(np.array(fast_stats_tracker["zone_reached"][-100:]), 0.1),
        "last100_q1_zone_reached": np.quantile(np.array(fast_stats_tracker["zone_reached"][-100:]), 0.25),
        "last100_median_zone_reached": np.quantile(np.array(fast_stats_tracker["zone_reached"][-100:]), 0.5),
        "last100_q3_zone_reached": np.quantile(np.array(fast_stats_tracker["zone_reached"][-100:]), 0.75),
        "last100_d9_zone_reached": np.quantile(np.array(fast_stats_tracker["zone_reached"][-100:]), 0.9),
        #
    }

    for i in range(len(misc.inputs)):
        step_stats[f"last100_q_value_{i}_starting_frame"] = np.mean(fast_stats_tracker[f"q_value_{i}_starting_frame"][-100:])

    for name, param in model1.named_parameters():
        step_stats[f"layer_{name}_L2"] = np.sqrt((param**2).mean().detach().cpu().item())

    for k, v in step_stats.items():
        tensorboard_writer.add_scalar(
            tag=k,
            scalar_value=v,
            walltime=time.time(),
        )

    step_stats_history.append(step_stats)
    # ===============================================
    #   CLEANUP
    # ===============================================
    fast_stats_tracker["n_frames_tmi_protection_triggered"].clear()
    fast_stats_tracker["train_on_batch_duration"].clear()
    fast_stats_tracker["race_time_ratio"].clear()
    fast_stats_tracker["loss"].clear()
    fast_stats_tracker["loss_test"].clear()

    fast_stats_tracker["laststep_time_to_answer_normal_step"].clear()
    fast_stats_tracker["laststep_time_to_answer_action_step"].clear()
    fast_stats_tracker["laststep_time_between_normal_on_run_steps"].clear()
    fast_stats_tracker["laststep_time_between_action_on_run_steps"].clear()

    fast_stats_tracker["laststep_time_to_grab_frame"].clear()
    fast_stats_tracker["laststep_time_between_grab_frame"].clear()
    fast_stats_tracker["laststep_time_A_rgb2gray"].clear()
    fast_stats_tracker["laststep_time_A_geometry"].clear()
    fast_stats_tracker["laststep_time_A_stack"].clear()
    fast_stats_tracker["laststep_time_exploration_policy"].clear()
    fast_stats_tracker["laststep_time_to_iface_set_set"].clear()
    fast_stats_tracker["laststep_time_after_iface_set_set"].clear()

    for key, value in fast_stats_tracker.items():
        print(f"{len(value)} : {key}")  # FIXME
        fast_stats_tracker[key] = value[-100:]

    number_memories_generated = 0
    number_frames_played = 0
