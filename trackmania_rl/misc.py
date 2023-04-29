import numpy as np

W = 640
H = 480

wind32gui_margins = {"left": 7, "top": 32, "right": 7, "bottom": 7}

running_speed = 20
tm_engine_step_per_action = 5
ms_per_tm_engine_step = 10
ms_per_action = ms_per_tm_engine_step * tm_engine_step_per_action
n_checkpoints_in_inputs = 16
max_overall_duration_ms = 50_000
max_minirace_duration_ms = 24_000


epsilon = 0.1
discard_non_greedy_actions_in_nsteps = True


anneal_step = 1
n_steps = [
    1,
    1,
    3,
    3,
    3,
    3,
    3,
    3,
][anneal_step]

gamma = [
    0.95,
    0.99,
    0.99,
    0.99,
    1,
    1,
    1,
][anneal_step]
reward_per_ms_in_race = [
    -0.15 / ms_per_action,
    -0.03 / ms_per_action,
    -0.03 / ms_per_action,
    -0.03 / ms_per_action,
    -0.03 / ms_per_action,
][anneal_step]

reward_on_finish = [
    1,
    1,
    1,
    1,
    1,
][anneal_step]
reward_on_failed_to_finish = 0
reward_per_ms_velocity = [
    0.15 / ms_per_action / 800,
    0.03 / ms_per_action / 800,
    0.03 / ms_per_action / 800,
    0.03 / ms_per_action / 1600,
    0.03 / ms_per_action / 4000,
][
    anneal_step
]
reward_per_ms_press_forward = [
    0.15 / ms_per_action / 4,
    0.03 / ms_per_action / 8,
    0,
    0,
    0,
][anneal_step]

statistics_save_period_seconds = 60 * 10


float_input_dim = 5 + 4 * n_checkpoints_in_inputs
float_hidden_dim = 256
conv_head_output_dim = 1152
dense_hidden_dimension = 1024
iqn_embedding_dimension = 64
iqn_n = 8
iqn_k = 32
iqn_kappa = 1
AL_alpha = [0, 0, 0, 0, 0, 0, 0.8][anneal_step]

memory_size = 30_000 * (n_checkpoints_in_inputs - 1)
memory_size_start_learn = 10_000
virtual_memory_size_start_learn = 10_000
number_memories_generated_high_exploration = 500_000
high_exploration_ratio = 5
batch_size = 1024
learning_rate = 5e-5

number_times_single_memory_is_used_before_discard = 8
number_memories_trained_on_between_target_network_updates = 10000

soft_update_tau = 0.2

float_inputs_mean = np.array(
    [
        2400,
        0, 0, 55,
        0, 1, 0,

        0, 0, -88,
        0, 0, -78,
        0, 0, -68,

        0, 0, -58,
        0, 0, -46,
        0, 0, -31,
        0, 0, -14,
        0, 0, 3.5,
        0, 0, 20,
        0, 0, 37,
        0, 0, 51,
        0, 0, 64,
        0, 0, 74,

        0, 0, 84,
        0, 0, 94,
        0, 0, 104,

        0.93333333, 0.86666667, 0.8, 0.73333333, 0.66666667,
        0.6, 0.53333333, 0.46666667, 0.4, 0.33333333,
        0.26666667, 0.2, 0.13333333, 0.06666667
    ]
)
# MEAN
# 2400,
# 0,0,55,
# 0,1,0,
#
# 0,0,-88,
# 0,0,-78,
# 0,0,-68,
#
# 0,0,-58,
# 0,0,-46,
# 0,0,-31,
# 0,0,-14,
# 0,0,3.5,
# 0,0,20,
# 0,0,37,
# 0,0,51,
# 0,0,64,
# 0,0,74,
#
# 0,0,84,
# 0,0,94,
# 0,0,104,
#
# 0.93333333, 0.86666667, 0.8       , 0.73333333, 0.66666667,
# 0.6       , 0.53333333, 0.46666667, 0.4       , 0.33333333,
# 0.26666667, 0.2       , 0.13333333, 0.06666667



# Raw mean in buffer  : [ 1.961e+03  2.000e-01 -1.000e-01  5.550e+01 -0.000e+00  1.000e+00
#   0.000e+00 -2.910e+01 -9.000e-01 -5.850e+01 -2.250e+01 -7.000e-01
#  -4.580e+01 -1.680e+01 -5.000e-01 -3.080e+01 -1.240e+01 -5.000e-01
#  -1.410e+01 -9.400e+00 -4.000e-01  3.500e+00 -8.000e+00 -5.000e-01
#   2.080e+01 -9.000e+00 -6.000e-01  3.690e+01 -1.300e+01 -8.000e-01
#   5.120e+01 -2.030e+01 -1.100e+00  6.370e+01 -3.050e+01 -1.300e+00
#   7.420e+01  9.000e-01  7.000e-01  6.000e-01  5.000e-01  4.000e-01
#   3.000e-01  2.000e-01  1.000e-01]
# Raw std in buffer   : [1.2201e+03 6.0000e-01 2.0000e-01 1.2000e+01 0.0000e+00 0.0000e+00
#  0.0000e+00 5.4900e+01 2.0000e+00 4.4600e+01 4.4400e+01 1.6000e+00
#  4.7300e+01 3.4900e+01 1.3000e+00 5.0800e+01 2.7600e+01 1.1000e+00
#  5.3600e+01 2.5800e+01 1.0000e+00 5.4500e+01 3.1200e+01 1.2000e+00
#  5.3000e+01 4.1400e+01 1.5000e+00 4.9500e+01 5.3100e+01 1.8000e+00
#  4.5600e+01 6.4400e+01 2.2000e+00 4.3900e+01 7.3900e+01 2.6000e+00
#  4.6600e+01 3.0000e-01 4.0000e-01 5.0000e-01 5.0000e-01 5.0000e-01
#  5.0000e-01 4.0000e-01 3.0000e-01]


# Corr mean in buffer : [-0.3  0.  -0.  -0.6 -0.  -0.   0.  -1.2 -0.  -0.5 -0.9 -0.  -0.4 -0.7
#  -0.  -0.2 -0.5 -0.   0.  -0.4 -0.   0.3 -0.3 -0.   0.6 -0.4 -0.   0.9
#  -0.5 -0.   1.  -0.8 -0.   1.1 -1.2 -0.1  1.2  0.4  0.2  0.1  0.  -0.1
#  -0.2 -0.3 -0.4]
# Corr std in buffer  : [0.1 0.1 0.  0.1 0.  0.  0.  2.2 0.1 1.8 1.8 0.1 1.9 1.4 0.1 2.  1.1 0.
#  2.1 1.  0.  2.2 1.2 0.  2.1 1.7 0.1 2.  2.1 0.1 1.8 2.6 0.1 1.8 3.  0.1
#  1.9 0.3 0.4 0.5 0.5 0.5 0.5 0.4 0.3]

float_inputs_std = np.array(
    [
        1500,
        10, 10, 15,
        1, 1, 1,

        88, 88, 44,
        77, 77, 44,
        66, 66, 44,

        55, 55, 44,
        44, 44, 48,
        35, 35, 50,
        28, 28, 54,
        26, 26, 54,
        31, 31, 53,
        41, 41, 50,
        53, 53, 46,
        64, 64, 44,
        74, 74, 44,

        84, 84, 44,
        94, 94, 44,
        104, 104, 44,

        3, 3, 4, 4, 4, 5, 5, 5, 5, 4, 4, 4, 3, 3
    ]
)

# STD
# 1500,
# 10,10,15,
# 1,1,1,
#
# 88,88,44,
# 77,77,44,
# 66,66,44,
#
# 55,55,44,
# 44,44,48,
# 35,35,50,
# 28,28,54,
# 26,26,54,
# 31,31,53,
# 41,41,50,
# 53,53,46,
# 64,64,44,
# 74,74,44,
#
# 84,84,44,
# 94,94,44,
# 104,104,44,
#
# 3,3,4,4,4,5,5,5,5,4,4,4,3,3

# float_inputs_mean = np.zeros(float_input_dim)
# float_inputs_std = np.ones(float_input_dim)

# 1, 4, 7 : accelerate
# 0, 3, 6 :
# 2, 5, 8 : backwards

inputs = [
    {  # 0 : Left, nothing else
        "left": True,
        "right": False,
        "accelerate": False,
        "brake": False,
    },
    {  # 1
        "left": True,
        "right": False,
        "accelerate": True,
        "brake": False,
    },
    {  # 2
        "left": True,
        "right": False,
        "accelerate": False,
        "brake": True,
    },
    {  # 3 : Right, nothing else
        "left": False,
        "right": True,
        "accelerate": False,
        "brake": False,
    },
    {  # 4
        "left": False,
        "right": True,
        "accelerate": True,
        "brake": False,
    },
    {  # 5
        "left": False,
        "right": True,
        "accelerate": False,
        "brake": True,
    },
    {  # 6 : Do nothing
        "left": False,
        "right": False,
        "accelerate": False,
        "brake": False,
    },
    {  # 7 : Accelerate forward, don't turn
        "left": False,
        "right": False,
        "accelerate": True,
        "brake": False,
    },
    {  # 8 : Go backward, don't turn
        "left": False,
        "right": False,
        "accelerate": False,
        "brake": True,
    },
]

action_forward_idx = 7  # Accelerate forward, don't turn
action_backward_idx = 8  # Go backward, don't turn
