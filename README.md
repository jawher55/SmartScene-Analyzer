Project Overview
The SmartScene Analyzer is a computer vision project designed to analyze images by detecting and classifying objects (e.g., people, chairs) in a scene. It uses YOLO for object detection and a CNN for classification, integrates with a FastAPI backend, and leverages the Ollama Mistral model to generate contextual commentary about the scene. The project is intended to showcase your skills in computer vision, machine learning, and API development to potential recruiters, with a focus on iterative improvement and documentation via GitHub.

Initial Challenges
YOLO Detection Issue: The baseline YOLOv8n model misses one person in the test image (temp_test2.jpg), detecting only 2 out of 3 people in a bar scene.
CNN Classification Issue: The CNN, originally trained on CIFAR-10, misclassifies chairs as "person" due to poor generalization.
Documentation: You wanted to ensure the project’s evolution is well-documented on GitHub to demonstrate your development process to recruiters.
Goal
Improve the detection and classification accuracy, explore advanced techniques like Differentiable Logic Cellular Automata (DiffLogic CA), and maintain a professional GitHub repository with clear commits, documentation, and potentially Colab notebooks to showcase your work..
