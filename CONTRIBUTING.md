# Contributing to BMW M3 DAQ System

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone <your-fork-url>`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly (including simulation mode)
6. Commit with clear messages
7. Push to your fork
8. Submit a pull request

## Development Setup

```bash
# Install development dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests in simulation mode
python scripts/test_sensors.py
python scripts/generate_test_data.py
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings to all functions and classes
- Comment complex logic
- Keep functions focused and modular

## Testing

- Test all changes in simulation mode before submitting
- If adding hardware support, document wiring and configuration
- Include example usage in docstrings
- Test on Raspberry Pi if possible

## Pull Request Guidelines

- Describe what your PR does and why
- Reference any related issues
- Include before/after behavior if applicable
- Update documentation if needed
- Add yourself to contributors list

## Areas for Contribution

### High Priority
- Additional sensor support (boost pressure, AFR, etc.)
- Improved power curve estimation algorithms
- Mobile app development
- Cloud data sync capabilities
- Video overlay export (RaceRender format)

### Medium Priority
- Additional vehicle profiles (other BMW models, etc.)
- Improved lap detection algorithms
- Predictive analytics (lap time prediction)
- Driver coaching features
- Data comparison tools

### Low Priority
- UI/UX improvements
- Additional export formats
- Performance optimizations
- Documentation improvements

## Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Hardware configuration (if applicable)
- Log output (use `sudo journalctl -u daq`)
- Screenshots if relevant

## Code of Conduct

- Be respectful and constructive
- Help newcomers learn
- Focus on technical merit
- Keep discussions on-topic

## Questions?

- Create an issue for questions
- Tag with "question" label
- Check existing issues first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Happy coding! 🚗💨
