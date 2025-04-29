import pandas as pd
import os
import seaborn as sns
import matplotlib.pyplot as plt
import re

def plot_accuracy(df, output_dir):
    accuracy_cols = ['overall_accuracy', 'overall_evidence_accuracy', 'overall_testimony_accuracy']
    for col in accuracy_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    base_prompt_df = df[
        (df['prompt'] == 'base') &
        (df['context'] == 'none') &
        (df['case'] == 'ALL') & 
        (df['description'].astype(str).str.lower() == 'true')
    ].copy()

    plot_data = base_prompt_df[['model'] + accuracy_cols].copy()
    col_names = {
        'overall_accuracy': 'Overall',
        'overall_evidence_accuracy': 'Evidence',
        'overall_testimony_accuracy': 'Testimony',
        'model': 'Model'
    }
    plot_data.rename(columns=col_names, inplace=True)

    base_accuracy = plot_data.set_index('Model')['Overall']
    sorted_models = base_accuracy.sort_values(ascending=True).index.tolist()

    melted_data = pd.melt(
        plot_data,
        id_vars=['Model'],
        var_name='Accuracy Type',
        value_name='Accuracy',
    )

    sns.set_theme(style='whitegrid', context='paper')
    plt.figure(figsize=(10, 6))

    ax = sns.barplot(
        data=melted_data,
        x='Model',
        y='Accuracy',
        hue='Accuracy Type',
        palette='viridis',
        order=sorted_models
    )
    ax.set_title('Model Accuracy on the Base Prompt', fontsize=14, weight='bold')
    ax.set_xlabel('Model', fontsize=12)
    ax.set_ylabel('Accuracy', fontsize=12)
    ax.set_ylim(0, 1)
    ax.set_yticks([i / 10.0 for i in range(11)])
    ax.tick_params(axis='x', rotation=45, labelsize=10)
    ax.legend(title='Accuracy Type', fontsize=10, title_fontsize=12)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'model_accuracy_base_prompt.png'), dpi=300)
    plt.close()

    print("Base prompt accuracy plot saved")

def plot_prompt_accuracy(df, output_dir, mode='cot'):
    # Filter rows
    if mode == 'cot':  # Prompt must be base or cot
        df_filtered = df[
            (df['prompt'].isin(['base', 'cot'])) &
            (df['context'] == 'none') &
            (df['case'] == 'ALL') &
            (df['description'].astype(str).str.lower() == 'true')
        ].copy()
        prompt_section = 'prompt'

    elif mode == 'no description':  # No description can be true or false
        df_filtered = df[
            (df['prompt'] == 'base') &
            (df['context'] == 'none') &
            (df['case'] == 'ALL')
        ].copy()
        prompt_section = 'description'
        
        # Convert description to true or false
        df_filtered[prompt_section] = df_filtered[prompt_section].astype(str).str.lower()

    elif mode == 'full context':  # Context can be today or none
        df_filtered = df[
            (df['prompt'] == 'base') &
            (df['case'] == 'ALL') &
            (df['context'].isin(['full', 'none'])) &
            (df['description'].astype(str).str.lower() == 'true')
        ].copy()
        prompt_section = 'context'

    # Filter out models that don't have both base and compared prompt runs
    model_prompt_counts = df_filtered.groupby('model').size()
    models = model_prompt_counts[model_prompt_counts == 2].index
    df_compared = df_filtered[df_filtered['model'].isin(models)].copy()
 
    df_compared['overall_accuracy'] = pd.to_numeric(df_compared['overall_accuracy'], errors="coerce")
    
    plot_data = df_compared[['model', prompt_section, 'overall_accuracy']].copy()
    col_names = {
        'overall_accuracy': 'Overall',
        'model': 'Model',
        prompt_section: 'Prompt'
    }
    plot_data.rename(columns=col_names, inplace=True)

    if mode == 'cot':
        prompt_name_map = {
            'base': 'Base',
            'cot': 'COT'
        }
        hue_order = ['Base', 'COT']
    elif mode == 'no description':
        prompt_name_map = {
            'true': 'Base',
            'false': 'No Description'
        }
        hue_order = ['Base', 'No Description']
    elif mode == 'full context':
        prompt_name_map = {
            'none': 'Base',
            'full': 'Full Context'
        }
        hue_order = ['Base', 'Full Context']
        
    plot_data['Prompt'] = plot_data['Prompt'].map(prompt_name_map).fillna(plot_data['Prompt'])

    # Sort
    base_accuracy = plot_data[plot_data['Prompt'] == 'Base'].set_index('Model')['Overall']
    sorted_models = base_accuracy.sort_values(ascending=True).index.tolist()

    sns.set_theme(style='whitegrid', context='paper')
    plt.figure(figsize=(10, 6))

    ax = sns.barplot(
        data=plot_data,
        x='Model',
        y='Overall',
        hue='Prompt',
        palette='viridis',
        order=sorted_models,
        hue_order=hue_order
    )
    ax.set_title(f'Model Accuracy on the base prompt vs {mode} prompt', fontsize=14, weight='bold')
    ax.set_xlabel('Model', fontsize=12)
    ax.set_ylabel('Accuracy', fontsize=12)
    ax.set_ylim(0, 1)
    ax.set_yticks([i / 10.0 for i in range(11)])
    if mode == 'cot':
        ax.tick_params(axis='x', rotation=45, labelsize=10)
    elif mode == 'context span':
        ax.tick_params(axis='x', rotation=0, labelsize=10)
    ax.legend(title='Prompt', fontsize=10, title_fontsize=12)

    plt.tight_layout()
    plt.savefig(os.path.join(
        output_dir, 
        f'model_accuracy_base_vs_{mode.replace(" ", "_")}.png'
    ), dpi=300)
    plt.close()

    print(f"{mode} prompt accuracy plot saved")

def get_model_size(model):
    if any(name in model for name in ['8b']):
        return 'Small'
    elif any(name in model for name in ['32b', '70b']):
        return 'Medium'
    elif 'mini' in model and 'gpt' in model:
        return 'Medium'
    else:
        return 'Large'

def plot_token_accuracy(df, output_dir):
    # Filter prompts
    df_filtered = df[
        (df['prompt'] == 'base') &
        (df['context'] == 'none') &
        (df['case'] == 'ALL') & 
        (df['description'].astype(str).str.lower() == 'true')
    ].copy()

    # Filter out models
    target_models = ['o3-mini', 'o4-mini']
    df_filtered = df_filtered[~df_filtered['model'].isin(target_models)]

    # Filter cols
    df_filtered['overall_accuracy'] = pd.to_numeric(df_filtered['overall_accuracy'], errors="coerce")
    df_filtered['average_reasoning_tokens'] = pd.to_numeric(df_filtered['average_reasoning_tokens'], errors="coerce")

    df_filtered.dropna(subset=['overall_accuracy', 'average_reasoning_tokens'], inplace=True)

    # Categorize models
    df_filtered['model_type'] = df_filtered['model'].apply(
        lambda x: 'Reasoning'
        if 'DeepSeek' in x
        else 'Non-Reasoning'
    )
    df_filtered['model_size'] = df_filtered['model'].apply(get_model_size)
    
    sns.set_theme(style='whitegrid', context='paper')
    plt.figure(figsize=(12, 7))

    ax = sns.scatterplot(
        data=df_filtered,
        x='average_reasoning_tokens',
        y='overall_accuracy',
        hue='model',
        size='model_size',
        sizes={'Small': 50, 'Medium': 100, 'Large': 150},
        style='model_type',
        markers={'Reasoning': 'X', 'Non-Reasoning': 'o'},
        legend=False
    )

    for i in range(df_filtered.shape[0]):
        plt.text(
            x=df_filtered['average_reasoning_tokens'].iloc[i] + 0.5,
            y=df_filtered['overall_accuracy'].iloc[i] + 0.01,
            s=df_filtered['model'].iloc[i],
            fontdict=dict(color='black', size=10)
        )

    ax.set_title('Model Accuracy vs Average Reasoning Tokens', fontsize=14, weight='bold')
    ax.set_xlabel('Average Reasoning Tokens', fontsize=12)
    ax.set_ylabel('Accuracy', fontsize=12)
    ax.set_ylim(0, 1)
    ax.set_yticks([i / 10.0 for i in range(11)])
    ax.tick_params(axis='x', rotation=45, labelsize=10)

    # Add legend
    # ax.legend(title='Model', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10, title_fontsize=12)
    
    plt.tight_layout(rect=(0, 0, 0.95, 1))
    plt.savefig(os.path.join(output_dir, 'model_accuracy_vs_average_reasoning_tokens.png'), dpi=300)
    plt.close()

    print("Token accuracy plot saved")

def plot_grouped_accuracy(df, output_dir, mode='category', k=5):
    # Select base prompt
    df_filtered = df[
            (df['prompt'] == 'base') &
            (df['context'] == 'none') &
            (df['case'] == 'ALL') &
            (df['description'].astype(str).str.lower() == 'true')
        ].copy()

    # Select top k models
    df_filtered['overall_accuracy'] = pd.to_numeric(df_filtered['overall_accuracy'], errors='coerce')
    top_k_models = df_filtered.sort_values('overall_accuracy', ascending=False)['model'].unique()[:k]
    df_filtered = df_filtered[df_filtered['model'].isin(top_k_models)].copy()

    # Filter cols
    accuracy_cols = []
    step_pattern = r'^[0-9]+_accuracy$'
    action_space_pattern = r'^[0-9]+-[0-9]+_accuracy$'
    if mode == 'category':
        candidate_cols = [
            col for col in df_filtered.columns 
            if col.endswith('_accuracy')
            and not col.startswith('overall')
            and not re.match(step_pattern, col)
            and not re.match(action_space_pattern, col)
        ]
        # print(candidate_cols)
    elif mode == 'steps':  # 1 digit
        candidate_cols = [
            col for col in df_filtered.columns 
            if col.endswith('_accuracy') and re.match(step_pattern, col)
        ]
    elif mode == 'action space':  # 3 digits
        candidate_cols = [
            col for col in df_filtered.columns 
            if col.endswith('_accuracy') and re.match(action_space_pattern, col)
        ]
        # print(candidate_cols)
    for col in candidate_cols:
        category = col.replace('_accuracy', '')
        total_col = f'{category}_total'
        if total_col in df_filtered.columns:
            # Compute average total count
            average_total = df_filtered[total_col].mean()
            if average_total >= 5:
                accuracy_cols.append(col)

    plot_data = df_filtered[['model'] + accuracy_cols].copy()
    for col in accuracy_cols:
        plot_data[col] = pd.to_numeric(plot_data[col], errors="coerce")
    
    col_names = {
        'model': 'Model',
        **{col: col.replace('_accuracy', '') for col in accuracy_cols}
    }
    if mode == 'category':
        var_name = 'Category'
    elif mode == 'steps':
        var_name = 'Number of Steps'
    elif mode == 'action space':
        var_name = 'Action Space'
    plot_data.rename(columns=col_names, inplace=True)

    melted_data = pd.melt(
        plot_data,
        id_vars=['Model'],
        var_name=var_name,
        value_name='Accuracy',
    )

    category_order = None
    if mode == 'category':
        top_1_model = top_k_models[0]
        top_1_model_data = melted_data[melted_data['Model'] ==top_1_model]
        category_order = top_1_model_data.set_index(var_name)['Accuracy'].sort_values(ascending=True).index.tolist()
    elif mode == 'action space':
        action_spaces = melted_data[var_name].unique()
        category_order = sorted(action_spaces, key=lambda x: int(x.split('-')[0]))

    sns.set_theme(style='whitegrid', context='paper')

    plt.figure(figsize=(12, 8))

    # Pivot so rows are categories and columns are models
    pivot_data = melted_data.pivot(index=var_name, columns='Model', values='Accuracy')
    if category_order is not None:
        pivot_data = pivot_data.reindex(category_order)

    palette = sns.color_palette('viridis', len(top_k_models))

    # Store text positions
    last_x_index = len(pivot_data.index) - 1
    text_x_pos = last_x_index + 0.1
    placed_label_positions = []
    y_closeness = 0.01
    nudge_amount = 0.02

    for i, model in enumerate(top_k_models):
        plt.plot(
            pivot_data.index,
            pivot_data[model],
            # label=model,
            marker='o',
            linestyle='-',
            color=palette[i]
        )

        last_point_y = pivot_data[model].iloc[-1]
        final_y = last_point_y
        is_nudged = True
        while is_nudged:
            is_nudged = False
            for placed_y in placed_label_positions:
                if abs(final_y - placed_y) < y_closeness:
                    final_y -= nudge_amount
                    is_nudged = True
                    break
        placed_label_positions.append(final_y)

        plt.text(
            x=text_x_pos,
            y=final_y,
            s=model,
            color=palette[i],
            fontsize=9,
            va='center'
        )

    plt.title(f'Model Accuracy on Each {var_name}', fontsize=14, weight='bold')
    plt.xlabel(var_name, fontsize=12)
    plt.ylabel('Accuracy', fontsize=12)
    plt.ylim(0, 1)
    plt.yticks([i / 10.0 for i in range(11)])
    if mode == 'category':
        rotation = 45
    else:
        rotation = 0
    plt.xticks(rotation=rotation, fontsize=10)
    # plt.legend(title='Model', fontsize=10, title_fontsize=12)
    
    plt.tight_layout(rect=(0, 0, 0.95, 1))
    plt.savefig(os.path.join(output_dir, f'model_accuracy_by_{mode}.png'), dpi=300)
    plt.close()

    print(f"{mode} accuracy plot saved")

def prepare_data(df):
    df.replace('N/A', pd.NA, inplace=True)
    model_name_map = {
        'llama-3.1-70b': 'Llama3.1-70B',
        'llama-3.1-8b': 'Llama3.1-8B',
        'deepseek-reasoner': 'DeepSeek-R1-671B',
        'deepseek-chat': 'DeepSeek-V3-671B',
        'deepseek-R1-70b': 'DeepSeek-R1-70B',
        'deepseek-R1-32b': 'DeepSeek-R1-32B',
        'deepseek-R1-8b': 'DeepSeek-R1-8B',
    }
    df['model'] = df['model'].map(model_name_map).fillna(df['model'])
    return df

if __name__ == "__main__":
    output_dir = "../output"
    df = pd.read_csv(os.path.join(output_dir, "eval.csv"))
    df = prepare_data(df)

    plot_accuracy(df, output_dir)
    plot_prompt_accuracy(df, output_dir, mode='cot')
    plot_prompt_accuracy(df, output_dir, mode='full context')
    plot_prompt_accuracy(df, output_dir, mode='no description')
    plot_token_accuracy(df, output_dir)
    plot_grouped_accuracy(df, output_dir, mode='category')
    plot_grouped_accuracy(df, output_dir, mode='steps')
    plot_grouped_accuracy(df, output_dir, mode='action space')
    
