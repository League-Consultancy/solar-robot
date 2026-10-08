import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt

from tensorflow import keras
from tensorflow.keras import layers
from sklearn.metrics import confusion_matrix, classification_report


# ============================================================
# CONFIGURATION
# ============================================================

DATASET_DIR = "dataset"
OUTPUT_DIR = "training"

IMG_SIZE = 224
BATCH_SIZE = 32

EPOCHS_HEAD = 10
EPOCHS_FINE = 30

NUM_CLASSES = 4

CLASS_NAMES = [
    "forward",
    "left",
    "right",
    "turn"
]

SEED = 42

# 20% validation from EACH class
VALIDATION_RATIO = 0.20


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)


print("TensorFlow version:", tf.__version__)
print()


# ============================================================
# DATASET
# BALANCED TRAIN / VALIDATION SPLIT
# ============================================================

print("Loading dataset...")
print()

rng = np.random.default_rng(SEED)

train_paths = []
train_labels = []

val_paths = []
val_labels = []


for class_index, class_name in enumerate(CLASS_NAMES):

    class_dir = os.path.join(
        DATASET_DIR,
        class_name
    )

    if not os.path.isdir(class_dir):
        raise RuntimeError(
            f"Class directory does not exist:\n"
            f"  {class_dir}"
        )

    # --------------------------------------------------------
    # Find images
    # --------------------------------------------------------

    files = []

    for filename in os.listdir(class_dir):

        filepath = os.path.join(
            class_dir,
            filename
        )

        if (
            os.path.isfile(filepath)
            and filename.lower().endswith(
                (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".bmp"
                )
            )
        ):
            files.append(filepath)

    # --------------------------------------------------------
    # Check class
    # --------------------------------------------------------

    if len(files) < 2:

        raise RuntimeError(
            f"Class '{class_name}' has only "
            f"{len(files)} image(s).\n"
            f"Need at least 2 images."
        )

    # --------------------------------------------------------
    # Shuffle this class independently
    # --------------------------------------------------------

    rng.shuffle(files)

    # --------------------------------------------------------
    # Validation count
    #
    # IMPORTANT:
    # Every class gets its own 20% validation set.
    # --------------------------------------------------------

    val_count = max(
        1,
        int(round(
            len(files) * VALIDATION_RATIO
        ))
    )

    # Prevent validation from taking the entire class
    if val_count >= len(files):
        val_count = len(files) - 1

    # --------------------------------------------------------
    # Split
    # --------------------------------------------------------

    class_val = files[:val_count]
    class_train = files[val_count:]

    # --------------------------------------------------------
    # Store training data
    # --------------------------------------------------------

    train_paths.extend(class_train)

    train_labels.extend(
        [class_index] * len(class_train)
    )

    # --------------------------------------------------------
    # Store validation data
    # --------------------------------------------------------

    val_paths.extend(class_val)

    val_labels.extend(
        [class_index] * len(class_val)
    )

    # --------------------------------------------------------
    # Print class distribution
    # --------------------------------------------------------

    print(
        f"{class_name:10s}: "
        f"total={len(files):4d}, "
        f"train={len(class_train):4d}, "
        f"validation={len(class_val):4d}"
    )


# ============================================================
# SHUFFLE COMPLETE TRAINING SET
# ============================================================

train_indices = np.arange(
    len(train_paths)
)

rng.shuffle(train_indices)

train_paths = [
    train_paths[i]
    for i in train_indices
]

train_labels = [
    train_labels[i]
    for i in train_indices
]


# ============================================================
# IMAGE LOADING FUNCTION
# ============================================================

def load_image(path, label):

    image = tf.io.read_file(path)

    image = tf.image.decode_image(
        image,
        channels=3,
        expand_animations=False
    )

    image.set_shape(
        [None, None, 3]
    )

    image = tf.image.resize(
        image,
        (IMG_SIZE, IMG_SIZE)
    )

    image = tf.cast(
        image,
        tf.float32
    )

    return image, label


# ============================================================
# CREATE TF DATASETS
# ============================================================

train_ds = tf.data.Dataset.from_tensor_slices(
    (
        train_paths,
        train_labels
    )
)

val_ds = tf.data.Dataset.from_tensor_slices(
    (
        val_paths,
        val_labels
    )
)


# Shuffle training dataset
train_ds = train_ds.shuffle(
    buffer_size=len(train_paths),
    seed=SEED,
    reshuffle_each_iteration=True
)


# Load images
train_ds = train_ds.map(
    load_image,
    num_parallel_calls=tf.data.AUTOTUNE
)

val_ds = val_ds.map(
    load_image,
    num_parallel_calls=tf.data.AUTOTUNE
)


# Batch
train_ds = train_ds.batch(
    BATCH_SIZE
)

val_ds = val_ds.batch(
    BATCH_SIZE
)


# Prefetch
AUTOTUNE = tf.data.AUTOTUNE

train_ds = train_ds.prefetch(
    AUTOTUNE
)

val_ds = val_ds.prefetch(
    AUTOTUNE
)


# ============================================================
# FINAL DATASET DISTRIBUTION
# ============================================================

print()
print("========================================")
print("DATASET DISTRIBUTION")
print("========================================")

for class_index, class_name in enumerate(CLASS_NAMES):

    train_count = train_labels.count(
        class_index
    )

    val_count = val_labels.count(
        class_index
    )

    print(
        f"{class_name:10s}: "
        f"train={train_count:4d}, "
        f"validation={val_count:4d}"
    )

print()

print(
    f"Total training images   : "
    f"{len(train_paths)}"
)

print(
    f"Total validation images : "
    f"{len(val_paths)}"
)

print()


# ============================================================
# DATA AUGMENTATION
# ============================================================

data_augmentation = keras.Sequential(
    [

        layers.RandomRotation(
            0.05
        ),

        layers.RandomZoom(
            0.10
        ),

        layers.RandomContrast(
            0.10
        ),

    ],
    name="augmentation"
)


# ============================================================
# MOBILE NET V3 SMALL
# ============================================================

print("Loading MobileNetV3-Small...")
print()

base_model = tf.keras.applications.MobileNetV3Small(

    input_shape=(
        IMG_SIZE,
        IMG_SIZE,
        3
    ),

    include_top=False,

    weights="imagenet",

    pooling="avg"

)


# ============================================================
# FREEZE BACKBONE INITIALLY
# ============================================================

base_model.trainable = False


# ============================================================
# BUILD CLASSIFIER
# ============================================================

inputs = keras.Input(
    shape=(
        IMG_SIZE,
        IMG_SIZE,
        3
    )
)


# Data augmentation
x = data_augmentation(
    inputs
)


# MobileNetV3 preprocessing is included
# when include_preprocessing=True
x = base_model(
    x,
    training=False
)


x = layers.Dropout(
    0.2
)(x)


outputs = layers.Dense(
    NUM_CLASSES,
    activation="softmax"
)(x)


model = keras.Model(
    inputs,
    outputs
)


# ============================================================
# STAGE 1 COMPILE
# ============================================================

model.compile(

    optimizer=keras.optimizers.Adam(
        learning_rate=1e-3
    ),

    loss="sparse_categorical_crossentropy",

    metrics=["accuracy"]

)


model.summary()


# ============================================================
# MODEL PATHS
# ============================================================

stage1_best_path = os.path.join(
    OUTPUT_DIR,
    "best_stage1_model.keras"
)

global_best_path = os.path.join(
    OUTPUT_DIR,
    "best_model.keras"
)

final_model_path = os.path.join(
    OUTPUT_DIR,
    "final_model.keras"
)


# ============================================================
# STAGE 1 CALLBACKS
# ============================================================

stage1_callbacks = [

    keras.callbacks.ModelCheckpoint(

        stage1_best_path,

        monitor="val_accuracy",

        save_best_only=True,

        mode="max",

        verbose=1

    ),

    keras.callbacks.EarlyStopping(

        monitor="val_accuracy",

        patience=7,

        mode="max",

        restore_best_weights=True,

        verbose=1

    ),

    keras.callbacks.ReduceLROnPlateau(

        monitor="val_loss",

        factor=0.3,

        patience=3,

        min_lr=1e-6,

        verbose=1

    )

]


# ============================================================
# STAGE 1
# TRAIN CLASSIFIER HEAD
# ============================================================

print()
print("========================================")
print("STAGE 1: Training classifier head")
print("========================================")


history_head = model.fit(

    train_ds,

    validation_data=val_ds,

    epochs=EPOCHS_HEAD,

    callbacks=stage1_callbacks

)


# ============================================================
# FIND BEST STAGE 1 ACCURACY
# ============================================================

best_stage1_val_accuracy = max(
    history_head.history[
        "val_accuracy"
    ]
)


print()
print(
    "Best Stage 1 validation accuracy: "
    f"{best_stage1_val_accuracy:.4f}"
)


# ============================================================
# LOAD BEST STAGE 1 MODEL
#
# IMPORTANT:
# Stage 2 starts from the BEST Stage 1
# weights, NOT from the last epoch.
# ============================================================

print()
print(
    "Loading best Stage 1 model "
    "before fine-tuning..."
)

model = tf.keras.models.load_model(
    stage1_best_path
)


# ============================================================
# CREATE INITIAL GLOBAL BEST
#
# Stage 1 is our current global best.
# ============================================================

model.save(
    global_best_path
)


global_best_accuracy = (
    best_stage1_val_accuracy
)


print(
    "Initial global best validation "
    f"accuracy: {global_best_accuracy:.4f}"
)


# ============================================================
# STAGE 2
# FINE-TUNE MOBILE NET V3
# ============================================================

print()
print("========================================")
print("STAGE 2: Fine tuning MobileNetV3")
print("========================================")


# ------------------------------------------------------------
# Get backbone from loaded model
# ------------------------------------------------------------

base_model = model.get_layer(
    "MobileNetV3Small"
)


# ------------------------------------------------------------
# Unfreeze backbone
# ------------------------------------------------------------

base_model.trainable = True


# ------------------------------------------------------------
# Freeze early layers
# ------------------------------------------------------------

fine_tune_from = 100


for layer in base_model.layers[
    :fine_tune_from
]:

    layer.trainable = False


# ============================================================
# COMPILE FOR FINE-TUNING
# ============================================================

model.compile(

    optimizer=keras.optimizers.Adam(
        learning_rate=1e-5
    ),

    loss="sparse_categorical_crossentropy",

    metrics=["accuracy"]

)


# ============================================================
# GLOBAL BEST CHECKPOINT
#
# Stage 2 is only allowed to replace
# Stage 1 if it actually improves.
# ============================================================

class GlobalBestCheckpoint(
    keras.callbacks.Callback
):

    def __init__(
        self,
        filepath,
        initial_best
    ):

        super().__init__()

        self.filepath = filepath

        self.best = initial_best


    def on_epoch_end(
        self,
        epoch,
        logs=None
    ):

        if logs is None:
            return

        current = logs.get(
            "val_accuracy"
        )

        if current is None:
            return

        if current > self.best:

            old_best = self.best

            self.best = current

            print()
            print(
                "Global validation accuracy "
                "improved: "
                f"{old_best:.4f} -> "
                f"{current:.4f}"
            )

            self.model.save(
                self.filepath
            )

            print(
                "Global best model saved."
            )


# ============================================================
# STAGE 2 CALLBACKS
# ============================================================

global_checkpoint = (
    GlobalBestCheckpoint(

        global_best_path,

        global_best_accuracy

    )
)


stage2_callbacks = [

    global_checkpoint,

    keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.3,
        patience=5,
        min_lr=1e-7,
        verbose=1
    )

]


# ============================================================
# STAGE 2 TRAINING
# ============================================================

history_fine = model.fit(

    train_ds,

    validation_data=val_ds,

    epochs=EPOCHS_FINE,

    callbacks=stage2_callbacks

)


# ============================================================
# LOAD GLOBAL BEST MODEL
#
# This guarantees the final model is never
# worse than the best Stage 1 / Stage 2 model.
# ============================================================

print()
print(
    "Loading global best model..."
)

model = tf.keras.models.load_model(
    global_best_path
)


# ============================================================
# SAVE FINAL MODEL
# ============================================================

model.save(
    final_model_path
)


print()
print("Final model saved:")
print(final_model_path)


# ============================================================
# SAVE CLASS NAMES
# ============================================================

class_names_path = os.path.join(
    OUTPUT_DIR,
    "class_names.txt"
)


with open(
    class_names_path,
    "w"
) as f:

    for name in CLASS_NAMES:

        f.write(
            name + "\n"
        )


print()
print("Class names saved:")
print(class_names_path)


# ============================================================
# EVALUATION
# ============================================================

print()
print("========================================")
print("EVALUATION")
print("========================================")


loss, accuracy = model.evaluate(
    val_ds,
    verbose=1
)


print()
print(
    f"Validation loss     : "
    f"{loss:.4f}"
)

print(
    f"Validation accuracy : "
    f"{accuracy:.4f}"
)


# ============================================================
# PREDICTIONS
# ============================================================

y_true = []
y_pred = []


for images, labels in val_ds:

    predictions = model.predict(
        images,
        verbose=0
    )

    predicted_classes = np.argmax(
        predictions,
        axis=1
    )

    y_true.extend(
        labels.numpy()
    )

    y_pred.extend(
        predicted_classes
    )


y_true = np.array(
    y_true
)

y_pred = np.array(
    y_pred
)


# ============================================================
# VALIDATION DISTRIBUTION
# ============================================================

print()
print("========================================")
print("VALIDATION CLASS DISTRIBUTION")
print("========================================")


for class_index, class_name in enumerate(
    CLASS_NAMES
):

    count = np.sum(
        y_true == class_index
    )

    print(
        f"{class_name:10s}: {count}"
    )


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print()
print("========================================")
print("Classification Report")
print("========================================")
print()


print(
    classification_report(

        y_true,

        y_pred,

        labels=[
            0,
            1,
            2,
            3
        ],

        target_names=CLASS_NAMES,

        digits=4,

        zero_division=0

    )
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(

    y_true,

    y_pred,

    labels=[
        0,
        1,
        2,
        3
    ]

)


print()
print("========================================")
print("Confusion Matrix")
print("========================================")

print(cm)


# ============================================================
# PLOT CONFUSION MATRIX
# ============================================================

plt.figure(
    figsize=(7, 7)
)

plt.imshow(
    cm
)

plt.title(
    "Confusion Matrix"
)

plt.colorbar()


plt.xticks(

    range(NUM_CLASSES),

    CLASS_NAMES,

    rotation=45

)


plt.yticks(

    range(NUM_CLASSES),

    CLASS_NAMES

)


plt.xlabel(
    "Predicted"
)

plt.ylabel(
    "Actual"
)


for i in range(NUM_CLASSES):

    for j in range(NUM_CLASSES):

        plt.text(

            j,

            i,

            cm[i, j],

            ha="center",

            va="center"

        )


plt.tight_layout()


cm_path = os.path.join(

    OUTPUT_DIR,

    "confusion_matrix.png"

)


plt.savefig(
    cm_path
)

plt.close()


print()
print(
    "Confusion matrix saved:"
)

print(
    cm_path
)


# ============================================================
# TRAINING GRAPHS
# ============================================================

acc = (
    history_head.history["accuracy"]
    +
    history_fine.history["accuracy"]
)


val_acc = (
    history_head.history["val_accuracy"]
    +
    history_fine.history["val_accuracy"]
)


losses = (
    history_head.history["loss"]
    +
    history_fine.history["loss"]
)


val_losses = (
    history_head.history["val_loss"]
    +
    history_fine.history["val_loss"]
)


# ============================================================
# ACCURACY GRAPH
# ============================================================

plt.figure(
    figsize=(10, 5)
)

plt.plot(
    acc,
    label="Training Accuracy"
)

plt.plot(
    val_acc,
    label="Validation Accuracy"
)


# Mark Stage 1 / Stage 2 boundary
plt.axvline(
    x=EPOCHS_HEAD - 1,
    linestyle="--",
    label="Fine-tuning starts"
)


plt.xlabel(
    "Epoch"
)

plt.ylabel(
    "Accuracy"
)

plt.title(
    "Training Accuracy"
)

plt.legend()

plt.grid(
    True
)


history_path = os.path.join(

    OUTPUT_DIR,

    "training_accuracy.png"

)


plt.savefig(
    history_path
)

plt.close()


# ============================================================
# LOSS GRAPH
# ============================================================

plt.figure(
    figsize=(10, 5)
)

plt.plot(
    losses,
    label="Training Loss"
)

plt.plot(
    val_losses,
    label="Validation Loss"
)


# Mark Stage 1 / Stage 2 boundary
plt.axvline(
    x=EPOCHS_HEAD - 1,
    linestyle="--",
    label="Fine-tuning starts"
)


plt.xlabel(
    "Epoch"
)

plt.ylabel(
    "Loss"
)

plt.title(
    "Training Loss"
)

plt.legend()

plt.grid(
    True
)


loss_path = os.path.join(

    OUTPUT_DIR,

    "training_loss.png"

)


plt.savefig(
    loss_path
)

plt.close()


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("========================================")
print("TRAINING COMPLETE")
print("========================================")

print()
print(
    "Best Stage 1 validation accuracy:"
)

print(
    f"  {best_stage1_val_accuracy:.4f}"
)

print()
print(
    "Best global validation accuracy:"
)

print(
    f"  {global_best_accuracy:.4f}"
)

print()
print(
    "Final model:"
)

print(
    final_model_path
)

print()
print(
    "Best model:"
)

print(
    global_best_path
)

print()