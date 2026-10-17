import { CommercialLabel, FlowContext, FlowLawResult, FlowLawViolation, FlowParticleSnapshot } from '../types';

export class FlowLaw {
  evaluate(
    particles: FlowParticleSnapshot[],
    context?: FlowContext,
    commercialLabels: CommercialLabel[] = [],
  ): FlowLawResult {
    const violations: FlowLawViolation[] = [];

    const uncollapsed = particles.filter((particle) => particle.latest.status === 'draft');
    if (uncollapsed.length > 10) {
      violations.push({
        code: 'PARTICLE_OVERFLOW',
        message: 'Too many draft particles without collapse',
        context,
      });
    }

    const orphaned = particles.filter((particle) => !particle.latest.context.persona);
    if (orphaned.length) {
      violations.push({
        code: 'ORPHANED_PARTICLE',
        message: 'Particles should reference a persona to maintain narrative consistency',
        context,
      });
    }

    const labelKeys = new Set<string>();
    for (const label of commercialLabels) {
      if (!/^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$/.test(label.key)) {
        violations.push({
          code: 'COMMERCIAL_LABEL_KEY_INVALID',
          message: `Commercial label key "${label.key}" must be lowercase and dot/hyphen separated`,
          context,
        });
      }
      if (!label.value.trim()) {
        violations.push({
          code: 'COMMERCIAL_LABEL_VALUE_EMPTY',
          message: `Commercial label "${label.key}" must have a non-empty value`,
          context,
        });
      }
      if (labelKeys.has(label.key)) {
        violations.push({
          code: 'COMMERCIAL_LABEL_KEY_DUPLICATE',
          message: `Commercial label key "${label.key}" must be unique`,
          context,
        });
      }
      labelKeys.add(label.key);
    }

    return { passed: violations.length === 0, violations };
  }
}
