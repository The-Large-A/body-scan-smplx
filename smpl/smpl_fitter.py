import torch
import smplx
import numpy as np
from config import SMPL_MODEL_PATH, USER_HEIGHT_CM

device = torch.device("cpu")

# MediaPipe → SMPL-X joint mapping
MP_TO_SMPL = {
    11: 16,  # left shoulder
    12: 17,  # right shoulder
    23: 1,   # left hip
    24: 2,   # right hip
    25: 4,   # left knee
    26: 5,   # right knee
    27: 7,   # left ankle
    28: 8    # right ankle
}

class SMPLFitter:

    def __init__(self):

        self.model = smplx.create(
            model_path=SMPL_MODEL_PATH,
            model_type="smplx",
            gender="neutral",
            num_betas=10,
            batch_size=1
        ).to(device)


    def fit(self, joints_list, masks):

        joint_tensors = [
            torch.tensor(j, dtype=torch.float32, device=device)
            for j in joints_list
        ]

        betas = torch.zeros((1,10), requires_grad=True, device=device)

        # lock body pose
        body_pose = torch.zeros((1,63), requires_grad=False, device=device)

        global_orient = torch.zeros((1,3), requires_grad=False, device=device)
        transl = torch.zeros((1,3), requires_grad=True, device=device)
        optimizer = torch.optim.Adam(
            [betas, transl],
            lr=0.01
        )

        for _ in range(150):

            optimizer.zero_grad()

            output = self.model(
                betas=betas,
                body_pose=body_pose,
                global_orient=global_orient,
                transl=transl
            )

            joints_3d = output.joints[0]

            loss = torch.tensor(0.0, device=device)

            for target in joint_tensors:

                for mp_idx, smpl_idx in MP_TO_SMPL.items():
                
                    mp_joint = target[mp_idx]
                    smpl_joint = joints_3d[smpl_idx]

                    loss += torch.mean((smpl_joint - mp_joint)**2)

            verts = output.vertices[0]

            min_x = torch.min(verts[:,0])
            max_x = torch.max(verts[:,0])
            min_z = torch.min(verts[:,2])
            max_z = torch.max(verts[:,2])

            width = max_x - min_x
            depth = max_z - min_z

            loss += 0.1 * (width + depth)

            loss.backward()

            optimizer.step()

        with torch.no_grad():

            output = self.model(
                betas=betas,
                body_pose=body_pose,
                global_orient=global_orient,
                transl=transl
            )

        vertices = output.vertices[0].cpu().numpy()

        vertices = self.scale_to_height(vertices)

        return vertices


    def scale_to_height(self, vertices):

        y = vertices[:,1]

        mesh_height = y.max() - y.min()

        target_height_m = USER_HEIGHT_CM / 100

        scale = target_height_m / mesh_height

        vertices = vertices * scale

        return vertices