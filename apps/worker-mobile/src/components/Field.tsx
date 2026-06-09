import { StyleSheet, Text, TextInput, type TextInputProps, View } from 'react-native';
import { colors, spacing } from '../theme/tokens';

interface FieldProps extends TextInputProps {
  label: string;
}

export function Field({ label, ...props }: FieldProps) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput {...props} style={[styles.input, props.style]} placeholderTextColor={colors.muted} />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.xs },
  label: { color: colors.muted, fontSize: 13, fontWeight: '700' },
  input: {
    borderColor: colors.border,
    borderRadius: 12,
    borderWidth: 1,
    color: colors.ink,
    minHeight: 44,
    paddingHorizontal: spacing.md,
  },
});
