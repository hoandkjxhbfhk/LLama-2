from typing import Callable, Iterable, Tuple

import torch
from torch.optim import Optimizer


class AdamW(Optimizer):
    def __init__(
            self,
            params: Iterable[torch.nn.parameter.Parameter],
            lr: float = 1e-3,
            betas: Tuple[float, float] = (0.9, 0.999),
            eps: float = 1e-6,
            weight_decay: float = 0.0,
            correct_bias: bool = True,
    ):
        if lr < 0.0:
            raise ValueError("Invalid learning rate: {} - should be >= 0.0".format(lr))
        if not 0.0 <= betas[0] < 1.0:
            raise ValueError("Invalid beta parameter: {} - should be in [0.0, 1.0[".format(betas[0]))
        if not 0.0 <= betas[1] < 1.0:
            raise ValueError("Invalid beta parameter: {} - should be in [0.0, 1.0[".format(betas[1]))
        if not 0.0 <= eps:
            raise ValueError("Invalid epsilon value: {} - should be >= 0.0".format(eps))
        defaults = dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay, correct_bias=correct_bias)
        super().__init__(params, defaults)

    def step(self, closure: Callable = None):
        loss = None
        if closure is not None:
            loss = closure()

        # Duyệt qua từng nhóm tham số (parameter group)
        for group in self.param_groups:
            lr = group["lr"]
            beta1, beta2 = group["betas"]
            eps = group["eps"]
            weight_decay = group["weight_decay"]
            correct_bias = group["correct_bias"]

            for p in group["params"]:
                if p.grad is None:
                    continue

                grad = p.grad.data
                if grad.is_sparse:
                    raise RuntimeError("Adam does not support sparse gradients, please consider SparseAdam instead")

                # Lấy trạng thái (state) của parameter p, nếu chưa có khởi tạo thì khởi tạo:
                state = self.state[p]
                if not state:
                    # Khởi tạo bước update, m (momentum) và v (squared gradient)
                    state["step"] = 0
                    state["m"] = torch.zeros_like(p.data)
                    state["v"] = torch.zeros_like(p.data)

                m, v = state["m"], state["v"]
                state["step"] += 1
                step = state["step"]

                # Cập nhật m và v theo công thức Adam:
                # m = beta1 * m + (1 - beta1) * grad
                # v = beta2 * v + (1 - beta2) * (grad ** 2)
                m.mul_(beta1).add_(grad, alpha=1 - beta1)
                v.mul_(beta2).addcmul_(grad, grad, value=1 - beta2)

                # Tính bias-corrected m và v nếu correct_bias=True
                if correct_bias:
                    m_hat = m / (1 - beta1 ** step)
                    v_hat = v / (1 - beta2 ** step)
                else:
                    m_hat = m
                    v_hat = v

                # Tính update theo công thức của AdamW:
                # update = lr * m_hat / (sqrt(v_hat) + eps)
                update = lr * m_hat / (v_hat.sqrt() + eps)

                # Cập nhật trọng số, áp dụng weight decay với learning rate tích hợp
                p.data.add_(update, alpha=-1)
                if weight_decay != 0:
                    p.data.add_(p.data, alpha=-lr * weight_decay)

        return loss
