using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;

namespace UrbanLens.Camera
{
    /// <summary>
    /// Orbit (right-drag), pan (middle-drag), zoom (scroll) and reset around a focus point.
    /// Uses the Unity Input System package (project Active Input Handling = Input System).
    /// </summary>
    public class OrbitCamera : MonoBehaviour
    {
        [Header("Focus")]
        [SerializeField] private Transform focusTarget;
        [SerializeField] private float distance = 1500f;
        [SerializeField] private float minDistance = 200f;
        [SerializeField] private float maxDistance = 8000f;
        [SerializeField] private float yaw = 45f;
        [SerializeField] private float pitch = 45f;

        [Header("Sensitivity")]
        [SerializeField] private float orbitSpeed = 0.25f;
        [SerializeField] private float panSpeed = 0.5f;
        [SerializeField] private float zoomStep = 0.1f;
        [SerializeField] private float minPitch = 10f;
        [SerializeField] private float maxPitch = 85f;

        private Vector3 panOffset = Vector3.zero;
        // True while an orbit/pan drag that started over UI is in progress; such drags are ignored.
        private bool dragStartedOverUI;
        private float defaultDistance;
        private float defaultYaw;
        private float defaultPitch;

        private void Start()
        {
            defaultDistance = distance;
            defaultYaw = yaw;
            defaultPitch = pitch;
            ApplyTransform();
        }

        private void LateUpdate()
        {
            HandleMouse();
            ApplyTransform();
        }

        private void HandleMouse()
        {
            Mouse mouse = Mouse.current;
            if (mouse == null) return;

            Vector2 delta = mouse.delta.ReadValue();
            bool pointerOverUI = EventSystem.current != null && EventSystem.current.IsPointerOverGameObject();

            // A drag that starts on the dashboard must not move the camera.
            if (mouse.rightButton.wasPressedThisFrame || mouse.middleButton.wasPressedThisFrame)
                dragStartedOverUI = pointerOverUI;
            if (!mouse.rightButton.isPressed && !mouse.middleButton.isPressed)
                dragStartedOverUI = false;

            if (mouse.rightButton.isPressed && !dragStartedOverUI)
            {
                yaw += delta.x * orbitSpeed;
                pitch = Mathf.Clamp(pitch - delta.y * orbitSpeed, minPitch, maxPitch);
            }

            if (mouse.middleButton.isPressed && !dragStartedOverUI)
            {
                Vector3 move = (-transform.right * delta.x - transform.up * delta.y) * panSpeed * distance * 0.001f;
                panOffset += move;
            }

            float scroll = mouse.scroll.ReadValue().y;
            if (Mathf.Abs(scroll) > 0.01f && !pointerOverUI)
            {
                distance = Mathf.Clamp(distance * (1f - Mathf.Sign(scroll) * zoomStep), minDistance, maxDistance);
            }
        }

        private void ApplyTransform()
        {
            Vector3 focus = (focusTarget != null ? focusTarget.position : Vector3.zero) + panOffset;
            Quaternion rot = Quaternion.Euler(pitch, yaw, 0f);
            transform.position = focus + rot * new Vector3(0f, 0f, -distance);
            transform.rotation = rot;
        }

        /// <summary>Return focus, distance and angles to their starting values.</summary>
        public void ResetCamera()
        {
            panOffset = Vector3.zero;
            distance = defaultDistance;
            yaw = defaultYaw;
            pitch = defaultPitch;
            ApplyTransform();
        }
    }
}
