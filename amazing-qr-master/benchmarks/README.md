# Amzqr Speed Benchmarks

基于 [pytest-benchmark](https://pytest-benchmark.readthedocs.io/) 的速度基准测试套件。
覆盖三类场景：纯二维码生成、静态图片合成、GIF 多帧合成。

## 运行方式

```sh
# 按场景分别运行（模式因场景而异：QR 生成与静态图片合成为多轮统计，
# 走 pytest-benchmark 默认多轮；GIF 多帧合成为单轮模式以控时，
# 勿用单条命令混跑全部，否则 GIF 会落在默认多轮模式）
uv run pytest benchmarks/test_bench_qr_generation.py --benchmark-only
uv run pytest benchmarks/test_bench_combine_static.py --benchmark-only
uv run pytest benchmarks/test_bench_combine_gif.py --benchmark-only --benchmark-min-rounds=1 --benchmark-min-time=0.000001

# 切换到改动前的历史代码版本，运行测试，保存基线快照，并记下id（三个场景分别保存，便于对比）
uv run pytest benchmarks/test_bench_qr_generation.py --benchmark-autosave
uv run pytest benchmarks/test_bench_combine_static.py --benchmark-autosave
uv run pytest benchmarks/test_bench_combine_gif.py --benchmark-min-rounds=1 --benchmark-min-time=0.000001 --benchmark-autosave

# 切换到改动后的代码版本，运行测试，对比指定基线（按场景选择对应保存的 id）
uv run pytest benchmarks/test_bench_qr_generation.py --benchmark-compare=<id>
uv run pytest benchmarks/test_bench_combine_static.py --benchmark-compare=<id>
uv run pytest benchmarks/test_bench_combine_gif.py --benchmark-compare=<id> --benchmark-min-rounds=1 --benchmark-min-time=0.000001
```

## 注意事项

对于 combine() 优化（commit 36e8515f6393874f8157f06fd212a7f25c85b925）之前的代码，benchmarks/test_bench_combine_gif.py 需要移除 version=40 的输入参数，避免造成耗时过长（几个小时）的情况。
