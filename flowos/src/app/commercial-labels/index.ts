import { CommercialLabel } from '../../types';
import { MemoryStorage } from '../../storage';
import { now, randomId } from '../../utils';

const LABEL_KEY_PATTERN = /^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$/;

export class CommercialLabelRegistry {
  constructor(private readonly storage: MemoryStorage) {}

  registerLabel(key: string, value: string): CommercialLabel {
    const candidate: CommercialLabel = {
      id: randomId(),
      key: key.trim(),
      value: value.trim(),
      createdAt: now(),
    };
    const violations = this.validate([...this.listLabels(), candidate]);
    if (violations.length > 0) {
      throw new Error(violations.map(({ code }) => code).join(', '));
    }
    return this.storage.upsertCommercialLabel(candidate);
  }

  listLabels(): CommercialLabel[] {
    return this.storage.listCommercialLabels();
  }

  validate(labels: CommercialLabel[]): Array<{ code: string; message: string }> {
    const violations: Array<{ code: string; message: string }> = [];
    const seenKeys = new Set<string>();

    for (const label of labels) {
      if (!LABEL_KEY_PATTERN.test(label.key)) {
        violations.push({
          code: 'COMMERCIAL_LABEL_KEY_INVALID',
          message: `Commercial label key "${label.key}" must be lowercase and dot/hyphen separated`,
        });
      }
      if (!label.value.trim()) {
        violations.push({
          code: 'COMMERCIAL_LABEL_VALUE_EMPTY',
          message: `Commercial label "${label.key}" must have a non-empty value`,
        });
      }
      if (seenKeys.has(label.key)) {
        violations.push({
          code: 'COMMERCIAL_LABEL_KEY_DUPLICATE',
          message: `Commercial label key "${label.key}" must be unique`,
        });
      }
      seenKeys.add(label.key);
    }

    return violations;
  }
}
